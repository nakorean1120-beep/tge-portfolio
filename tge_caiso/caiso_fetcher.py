#!/usr/bin/env python3
"""
TGE CAISO Data Fetcher v2
==========================
CAISO OASIS에서 SP15(Tahoe) + SP26(Grizzly) DA LMP 데이터를 가져와
HTML 대시보드가 읽을 수 있는 JSON 파일로 저장합니다.

사용법:
  python caiso_fetcher.py                 # 어제 데이터 fetch
  python caiso_fetcher.py 2026-05-01      # 특정 날짜
  python caiso_fetcher.py --backfill 7    # 지난 7일 백필
  python caiso_fetcher.py --help

자동화 (cron):
  # 매일 오전 11시 PDT 실행 (DA 결과는 D+1 10:00 AM PDT 공개)
  0 11 * * * /usr/bin/python3 /path/to/caiso_fetcher.py >> /path/to/caiso.log 2>&1

출력 (data/ 폴더):
  caiso_latest.json              ← HTML이 참조 (최신 1일)
  caiso_actual_YYYY-MM-DD.json   ← 날짜별 보관
  caiso_index.json               ← 날짜 인덱스
  caiso_history.json             ← 누적 이력 (최근 30일)
"""

import requests
import zipfile
import io
import json
import sys
import os
import time
import argparse
from datetime import datetime, timezone, timedelta

# ── 설정 ────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR  = os.path.join(SCRIPT_DIR, 'data')

# TGE 자산 정의
ASSETS = {
    'tahoe': {
        'name':     'Tahoe',
        'node':     'TH_SP15_GEN-APND',  # SP15 Trading Hub
        'mw':       182.5,
        'rt_reserve': 0.25,
    },
    'grizzly': {
        'name':     'Grizzly',
        'node':     'TH_SP26_GEN-APND',  # SP26 Trading Hub
        'mw':       275.0,
        'rt_reserve': 0.25,
    },
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; TGE-Fetcher/2.0; +https://tge-energy.com)',
    'Accept':     'application/zip, */*',
}

# CAISO API rate limit: 약 30s/request 권장
CAISO_DELAY = 6  # 같은 노드 재요청 시 대기 (초)


# ──────────────────────────────────────────────────────────
# 1. CAISO API 호출
# ──────────────────────────────────────────────────────────

def build_url(node: str, trade_date: str) -> str:
    """CAISO OASIS API URL 생성"""
    d  = datetime.strptime(trade_date, '%Y-%m-%d')
    d1 = d + timedelta(days=1)
    # CAISO는 UTC 기준 + PDT는 UTC-7
    start = d.strftime('%Y%m%d')  + 'T07:00-0000'  # 00:00 PDT
    end   = d1.strftime('%Y%m%d') + 'T07:00-0000'
    return (
        'https://oasis.caiso.com/oasisapi/SingleZip'
        f'?resultformat=6&queryname=PRC_LMP&version=12'
        f'&market_run_id=DAM&node={node}'
        f'&startdatetime={start}&enddatetime={end}'
    )


def fetch_lmp(node: str, trade_date: str, retries: int = 3) -> list:
    """CAISO에서 시간별 LMP 가져오기"""
    url = build_url(node, trade_date)
    print(f'  [CAISO] {node} ({trade_date})')

    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=45)
            
            if r.status_code == 429:  # rate limit
                wait = 30 * (attempt + 1)
                print(f'    ⏳ Rate limit, {wait}초 대기...')
                time.sleep(wait)
                continue
            
            if r.status_code != 200:
                print(f'    ✗ HTTP {r.status_code}: {r.content[:80]}')
                if attempt < retries - 1:
                    time.sleep(5 * (attempt + 1))
                continue

            if len(r.content) < 200:
                print(f'    ⚠ 응답 너무 작음 ({len(r.content)} bytes): {r.content[:80]}')
                if attempt < retries - 1:
                    time.sleep(5)
                continue

            # ZIP 파싱
            z   = zipfile.ZipFile(io.BytesIO(r.content))
            csv = z.read(z.namelist()[0]).decode('utf-8')
            hourly = parse_lmp_csv(csv)
            
            if len(hourly) == 24 and any(h['lmp'] != 0 for h in hourly):
                return hourly
            else:
                print(f'    ⚠ 데이터 부족 또는 0값. 재시도...')

        except zipfile.BadZipFile:
            print(f'    ✗ ZIP 형식 오류 (시도 {attempt+1})')
        except requests.RequestException as e:
            print(f'    ✗ 네트워크 오류 (시도 {attempt+1}): {e}')
        except Exception as e:
            print(f'    ✗ 시도 {attempt+1}: {type(e).__name__}: {e}')
        
        if attempt < retries - 1:
            time.sleep(10 * (attempt + 1))
    
    raise RuntimeError(f'CAISO 데이터 조회 실패: {node} / {trade_date}')


def parse_lmp_csv(csv_text: str) -> list:
    """CAISO CSV 파싱 → 24개 시간별 LMP"""
    lines = csv_text.strip().split('\n')
    if len(lines) < 2:
        return []
    
    header = [h.strip().upper() for h in lines[0].split(',')]
    
    # 컬럼 위치 자동 탐색
    hour_col  = -1
    price_col = -1
    type_col  = -1
    
    for i, h in enumerate(header):
        if h in ('OPR_HR', 'HOUR') and hour_col < 0:
            hour_col = i
        elif h in ('MW', 'VALUE', 'LMP', 'PRICE') and price_col < 0:
            price_col = i
        elif h == 'LMP_TYPE':
            type_col = i
    
    if hour_col < 0 or price_col < 0:
        print(f'    ⚠ CSV 형식 인식 실패. 헤더: {header[:8]}')
        return []
    
    hourly = {}
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) <= max(hour_col, price_col):
            continue
        # LMP_TYPE이 있으면 LMP 행만
        if type_col >= 0 and cols[type_col].strip().upper() != 'LMP':
            continue
        try:
            hr  = int(float(cols[hour_col].strip()))
            prc = float(cols[price_col].strip())
            # CAISO는 HE1~HE24 → 0~23으로 변환
            if hr == 24:
                hr = 0
            elif hr >= 1:
                hr = hr - 1 if hr <= 23 else hr % 24
            if 0 <= hr <= 23:
                hourly[hr] = prc
        except (ValueError, IndexError):
            continue
    
    return [{'hour': h, 'lmp': hourly.get(h, 0.0)} for h in range(24)]


# ──────────────────────────────────────────────────────────
# 2. 메트릭 계산 (TB4, 충방전, 음가격 등)
# ──────────────────────────────────────────────────────────

def calc_metrics(hourly: list, asset: dict) -> dict:
    """TB4, 충방전 시간, 음가격, 자산별 수익 계산"""
    prices = [x['lmp'] for x in hourly]
    
    if len(prices) != 24:
        return {}
    
    # 가격 정렬
    indexed = sorted(enumerate(prices), key=lambda x: x[1])
    bot4 = [h for h, _ in indexed[:4]]   # 가장 싼 4시간
    top4 = [h for h, _ in indexed[-4:]]  # 가장 비싼 4시간
    
    tb4      = sum(prices[h] for h in top4) - sum(prices[h] for h in bot4)
    neg_hrs  = [h for h, p in enumerate(prices) if p < -2]
    avg_top4 = sum(prices[h] for h in top4) / 4
    avg_bot4 = sum(prices[h] for h in bot4) / 4
    
    # 자산별 수익 (4시간 충/방전, RT 예비 차감)
    dispatch_mw = asset['mw'] * (1 - asset['rt_reserve'])
    rev_k       = round(dispatch_mw * 4 * (avg_top4 - avg_bot4) / 1000, 2)
    
    return {
        'tb4':        round(tb4, 2),
        'neg_count':  len(neg_hrs),
        'neg_hours':  sorted(neg_hrs),
        'ch_hours':   sorted(bot4),
        'dis_hours':  sorted(top4),
        'avg_top4':   round(avg_top4, 2),
        'avg_bot4':   round(avg_bot4, 2),
        'avg_24h':    round(sum(prices) / 24, 2),
        'max_lmp':    round(max(prices), 2),
        'min_lmp':    round(min(prices), 2),
        'rev_k':      rev_k,
        'hourly':     [round(p, 2) for p in prices],
    }


# ──────────────────────────────────────────────────────────
# 3. JSON 저장 (대시보드 호환)
# ──────────────────────────────────────────────────────────

def save_results(trade_date: str, results: dict):
    """JSON 파일 저장 (대시보드의 fetchCAISOPrices가 읽을 수 있는 형식)"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 대시보드 호환 형식 - 자산별 묶음
    payload = {
        'trade_date': trade_date,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'source':     'CAISO OASIS PRC_LMP',
        'assets':     results,
        # 대시보드의 fetchCAISOPrices()가 사용하는 D+1/D+2/D+3 형식
        'd1': {'tb4_spread': results.get('tahoe', {}).get('tb4', 0)},
        'd2': {'tb4_spread': results.get('tahoe', {}).get('tb4', 0)},
        'd3': {'tb4_spread': results.get('tahoe', {}).get('tb4', 0)},
        # Result 탭의 자동 입력용 (Tahoe 기준)
        **(results.get('tahoe', {})),
    }
    
    # 1) 최신 파일 (대시보드 자동 로드)
    latest = os.path.join(OUTPUT_DIR, 'caiso_latest.json')
    with open(latest, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f'  ✓ {latest}')
    
    # 2) 날짜별 보관
    dated = os.path.join(OUTPUT_DIR, f'caiso_actual_{trade_date}.json')
    with open(dated, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f'  ✓ {dated}')
    
    # 3) 인덱스 업데이트
    index_path = os.path.join(OUTPUT_DIR, 'caiso_index.json')
    try:
        with open(index_path) as f:
            index = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        index = []
    if trade_date not in index:
        index.append(trade_date)
        index.sort(reverse=True)  # 최근 → 과거
    with open(index_path, 'w') as f:
        json.dump(index[:90], f)  # 최근 90일까지만 인덱스에 보관
    
    # 4) 누적 history (대시보드의 누적 비교 섹션용)
    update_history(trade_date, payload)


def update_history(trade_date: str, payload: dict):
    """누적 이력 (최근 30일) 업데이트"""
    hist_path = os.path.join(OUTPUT_DIR, 'caiso_history.json')
    try:
        with open(hist_path) as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []
    
    # 같은 날짜 제거 후 추가
    history = [h for h in history if h.get('trade_date') != trade_date]
    history.append({
        'trade_date': trade_date,
        'tahoe':      payload.get('assets', {}).get('tahoe',   {}),
        'grizzly':    payload.get('assets', {}).get('grizzly', {}),
    })
    history.sort(key=lambda x: x.get('trade_date', ''), reverse=True)
    history = history[:30]  # 최근 30일만 유지
    
    with open(hist_path, 'w') as f:
        json.dump(history, f, indent=2)
    print(f'  ✓ history: {len(history)}일 누적')


# ──────────────────────────────────────────────────────────
# 4. 메인 실행
# ──────────────────────────────────────────────────────────

def run_one_day(trade_date: str) -> dict:
    """하루 데이터 fetch (모든 자산)"""
    print(f'\n{"="*55}')
    print(f'  TGE CAISO Fetcher  —  {trade_date}')
    print(f'{"="*55}')
    
    results = {}
    asset_keys = list(ASSETS.keys())
    
    for i, key in enumerate(asset_keys):
        asset = ASSETS[key]
        try:
            hourly  = fetch_lmp(asset['node'], trade_date)
            metrics = calc_metrics(hourly, asset)
            results[key] = metrics
            print(f'    TB4={metrics["tb4"]:7.2f}  '
                  f'충전 {metrics["ch_hours"]}  '
                  f'방전 {metrics["dis_hours"]}  '
                  f'음가격 {metrics["neg_count"]}h')
        except Exception as e:
            print(f'    ✗ 실패: {e}')
            results[key] = None
        
        # rate limit 회피
        if i < len(asset_keys) - 1:
            time.sleep(CAISO_DELAY)
    
    # 적어도 한 자산 성공해야 저장
    if any(v for v in results.values()):
        save_results(trade_date, results)
        print(f'\n✅ {trade_date} 완료')
    else:
        print(f'\n❌ 모든 자산 실패. 데이터 미공개일 수 있음 (주말/휴일/너무 최근).')
        sys.exit(1)
    
    return results


def run_backfill(days: int):
    """과거 N일 백필"""
    print(f'\n📅 백필 모드: 지난 {days}일')
    today = datetime.now(timezone.utc).date()
    success = 0
    for i in range(1, days + 1):
        d = today - timedelta(days=i)
        trade_date = d.strftime('%Y-%m-%d')
        try:
            run_one_day(trade_date)
            success += 1
            time.sleep(CAISO_DELAY)
        except Exception as e:
            print(f'  ⏭ {trade_date} 스킵: {e}')
    print(f'\n📊 백필 결과: {success}/{days}일 성공')


def main():
    parser = argparse.ArgumentParser(
        description='TGE CAISO Data Fetcher v2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('date', nargs='?', help='YYYY-MM-DD (기본: 어제)')
    parser.add_argument('--backfill', type=int, metavar='N',
                        help='지난 N일 백필 (예: --backfill 7)')
    args = parser.parse_args()
    
    if args.backfill:
        run_backfill(args.backfill)
    elif args.date:
        run_one_day(args.date)
    else:
        # 기본: 어제 데이터 (DA 결과는 당일 오전 공개되므로 어제 것을 가져옴)
        trade_date = (datetime.now(timezone.utc).date() - timedelta(days=1)).strftime('%Y-%m-%d')
        run_one_day(trade_date)


if __name__ == '__main__':
    main()
