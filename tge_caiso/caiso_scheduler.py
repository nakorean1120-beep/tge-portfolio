#!/usr/bin/env python3
"""
TGE CAISO Auto Scheduler
=========================
3가지 자동 실행 방법:

1. Python schedule 라이브러리 (가장 간단, 백그라운드 실행)
   → python caiso_scheduler.py

2. macOS launchd (Mac 권장, 시스템 재부팅 후에도 자동 실행)
   → bash install_macos.sh

3. Linux cron (Linux 서버 권장)
   → bash install_cron.sh

이 스크립트는 방법 1을 실행합니다.
"""

import time
import subprocess
import sys
import os
from datetime import datetime, timedelta

try:
    import schedule
except ImportError:
    print('❌ schedule 라이브러리가 설치되지 않았어요.')
    print('   설치: pip install schedule')
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT     = os.path.join(SCRIPT_DIR, 'caiso_fetcher.py')
LOG_FILE   = os.path.join(SCRIPT_DIR, 'caiso.log')

# 실행 시간 (PDT/PST 기준 - DA는 10:00 AM PDT 공개)
SCHEDULE_TIMES = ['11:00', '14:00']  # 11시 + 14시 (재시도)


def log(msg: str):
    """로그 파일 + 콘솔에 출력"""
    line = f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def job():
    """cron job 실행"""
    log(f'CAISO fetch 시작')
    try:
        r = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True,
            text=True,
            timeout=300,
        )
        # stdout 로그 기록
        for line in (r.stdout or '').strip().split('\n'):
            if line:
                log(f'  {line}')
        if r.returncode == 0:
            log(f'✅ 완료')
        else:
            log(f'❌ 실패 (exit={r.returncode})')
            for line in (r.stderr or '').strip().split('\n'):
                if line:
                    log(f'  ERR: {line}')
    except subprocess.TimeoutExpired:
        log('❌ 타임아웃 (5분 초과)')
    except Exception as e:
        log(f'❌ 예외: {e}')


# 스케줄 등록
for t in SCHEDULE_TIMES:
    schedule.every().day.at(t).do(job)

log(f'🚀 TGE CAISO 스케줄러 시작')
log(f'   실행 시간: {", ".join(SCHEDULE_TIMES)} (로컬)')
log(f'   로그: {LOG_FILE}')
log(f'   종료: Ctrl+C')

# 시작 시 즉시 1회 실행 (테스트)
log('초기 1회 실행...')
job()

# 무한 루프
try:
    while True:
        schedule.run_pending()
        time.sleep(60)
except KeyboardInterrupt:
    log('🛑 스케줄러 종료 (Ctrl+C)')
    sys.exit(0)
