# TGE CAISO Auto Fetcher v2

CAISO OASIS에서 **SP15(Tahoe) + SP26(Grizzly)** DA LMP를 매일 자동으로 가져와
TGE 대시보드의 **Result 탭**에 자동 연동합니다.

---

## 📁 폴더 구조

```
tge_caiso_v2/
├── caiso_fetcher.py        # 메인 fetcher (수동/자동 실행)
├── caiso_scheduler.py      # Python 기반 스케줄러
├── install_macos.sh        # macOS launchd 설치 (권장: Mac)
├── install_cron.sh         # Linux cron 설치 (권장: Linux 서버)
├── uninstall_macos.sh      # macOS 제거
├── uninstall_cron.sh       # Linux 제거
├── README.md               # 이 파일
├── requirements.txt        # Python 의존성
└── data/                   # JSON 출력 (자동 생성)
    ├── caiso_latest.json          ← 대시보드 자동 로드 (최신)
    ├── caiso_history.json         ← 누적 30일
    ├── caiso_actual_YYYY-MM-DD.json   ← 날짜별 보관
    └── caiso_index.json           ← 날짜 인덱스
```

---

## 🚀 빠른 시작 (5분)

### 1. 의존성 설치

```bash
cd tge_caiso_v2
pip3 install -r requirements.txt
```

또는 직접:
```bash
pip3 install requests schedule
```

### 2. 즉시 1회 실행 (테스트)

```bash
python3 caiso_fetcher.py
```

성공 시 출력:
```
=======================================================
  TGE CAISO Fetcher  —  2026-05-03
=======================================================
  [CAISO] TH_SP15_GEN-APND (2026-05-03)
    TB4=  32.45  충전 [2, 3, 4, 5]  방전 [18, 19, 20, 21]  음가격 0h
  [CAISO] TH_SP26_GEN-APND (2026-05-03)
    TB4=  28.12  충전 [2, 3, 4, 5]  방전 [18, 19, 20, 21]  음가격 0h
  ✓ data/caiso_latest.json
  ✓ data/caiso_actual_2026-05-03.json
  ✓ history: 1일 누적

✅ 2026-05-03 완료
```

### 3. 대시보드와 같은 폴더에 배치

대시보드 HTML과 `tge_caiso_v2/` 폴더를 **같은 부모 폴더**에 두세요:

```
my_workspace/
├── TGE_Portfolio_v5.html
└── tge_caiso_v2/
    ├── caiso_fetcher.py
    └── data/
        └── caiso_history.json   ← 대시보드가 ./data/caiso_history.json으로 읽음
```

또는 대시보드 HTML과 같은 폴더 안의 `data/` 폴더에 JSON만 복사해도 됩니다:

```
my_workspace/
├── TGE_Portfolio_v5.html
└── data/
    ├── caiso_latest.json
    └── caiso_history.json
```

### 4. 대시보드 열기 → Result 탭

**📡 CAISO 자동 로드** 버튼 클릭 → 자동으로 history에 병합됨!

또는 Result 탭 진입 시 **자동으로 로드 시도**됩니다 (조용히, 실패해도 무시).

---

## ⏰ 자동 실행 설정 (한 번만)

### macOS (권장)

```bash
bash install_macos.sh
```

→ launchd 서비스 등록 (시스템 재부팅 후에도 자동)
→ 매일 11:00 + 14:00 자동 실행

### Linux 서버

```bash
bash install_cron.sh
```

→ cron 등록
→ 매일 11:00 + 14:00 자동 실행

### Python 스케줄러 (간단, 터미널 열어두기)

```bash
python3 caiso_scheduler.py &
```

→ 백그라운드로 실행
→ 터미널 닫으면 종료됨

### Windows

작업 스케줄러로 등록:
1. Win + R → `taskschd.msc`
2. 작업 만들기 → 트리거 매일 11:00
3. 동작: `python.exe` + 인수 `caiso_fetcher.py 경로`

---

## 📊 사용법

### 어제 데이터 fetch (기본)
```bash
python3 caiso_fetcher.py
```

### 특정 날짜
```bash
python3 caiso_fetcher.py 2026-05-01
```

### 과거 N일 백필
```bash
python3 caiso_fetcher.py --backfill 7    # 지난 7일
python3 caiso_fetcher.py --backfill 30   # 지난 30일
```

처음 사용 시 `--backfill 14`로 2주 데이터 채워두면 알고리즘 진단·Conformal 보정이 즉시 활성화돼요.

---

## 🔌 대시보드 연동 흐름

```
[매일 11:00]
caiso_fetcher.py 자동 실행
    ↓
CAISO OASIS API → TH_SP15 + TH_SP26 24시간 LMP 조회
    ↓
TB4, 충방전 시간, 음가격, 수익 계산
    ↓
data/caiso_history.json 업데이트 (최근 30일)
data/caiso_latest.json 갱신
    ↓
[사용자] 대시보드 Result 탭 열기
    ↓
자동으로 caiso_history.json 로드 시도
    ↓
새 actual 데이터를 history에 자동 병합
    ↓
KPI / 누적 비교 / 알고리즘 진단 자동 갱신 ✅
```

---

## 📋 JSON 출력 형식

### data/caiso_latest.json
```json
{
  "trade_date": "2026-05-03",
  "fetched_at": "2026-05-04T18:00:00+00:00",
  "source": "CAISO OASIS PRC_LMP",
  "assets": {
    "tahoe": {
      "tb4": 32.45,
      "neg_count": 0,
      "neg_hours": [],
      "ch_hours": [2, 3, 4, 5],
      "dis_hours": [18, 19, 20, 21],
      "avg_top4": 78.50,
      "avg_bot4": 12.30,
      "avg_24h": 38.20,
      "max_lmp": 95.40,
      "min_lmp": 8.50,
      "rev_k": 24.32,
      "hourly": [15.20, 14.80, ...]
    },
    "grizzly": { ... }
  }
}
```

### data/caiso_history.json (최근 30일)
```json
[
  {"trade_date": "2026-05-03", "tahoe": {...}, "grizzly": {...}},
  {"trade_date": "2026-05-02", "tahoe": {...}, "grizzly": {...}},
  ...
]
```

---

## 🔍 모니터링

### 로그 확인
```bash
tail -f caiso.log
```

### 마지막 fetch 시각 확인
```bash
ls -la data/caiso_latest.json
cat data/caiso_latest.json | python3 -m json.tool | head -10
```

### 누적 일수
```bash
cat data/caiso_index.json | python3 -m json.tool
```

### macOS launchd 상태
```bash
launchctl list | grep tge.caiso
```

### Linux cron 상태
```bash
crontab -l | grep TGE_CAISO
```

---

## ⚠️ 주의사항

### 1. 너무 최근 날짜는 데이터 없음
- DA LMP는 **D+1 10:00 AM PDT**에 공개
- 11:00 PDT 이전에 실행하면 어제 데이터 미공개 → 실패
- 그래서 11:00 + 14:00 두 번 실행 (재시도)

### 2. 주말/공휴일
- CAISO는 주말·공휴일도 거래일이라 데이터 있음
- 단, 변동성 작아서 데이터 의미 약함

### 3. CAISO API rate limit
- 너무 자주 호출 시 429 에러
- 자산 간 6초 대기 + 재시도 시 30초 대기

### 4. 네트워크 차단 환경
- 회사 방화벽이 CAISO API 차단할 수 있음
- 차단 시: `curl https://oasis.caiso.com/oasisapi/SingleZip` 직접 테스트

### 5. file:// 프로토콜
- 브라우저에서 `file:///` 경로로 HTML 열면 fetch 차단
- 해결: `python3 -m http.server` 또는 VS Code Live Server 사용

```bash
cd my_workspace
python3 -m http.server 8000
# → http://localhost:8000/TGE_Portfolio_v5.html 접속
```

---

## 🛠 문제 해결

### "ModuleNotFoundError: No module named 'requests'"
```bash
pip3 install requests
```

### "BadZipFile" 에러
CAISO 응답이 ZIP이 아닌 에러 메시지인 경우. 보통:
- 잘못된 노드명 (TH_SP15_GEN-APND가 정확)
- 너무 미래/과거 날짜
- API 일시 장애 → 5분 후 재시도

### "데이터 미공개일 수 있음" 에러
- 14:00 PDT 이후에 다시 실행
- 또는 더 과거 날짜로 시도: `python3 caiso_fetcher.py 2026-04-30`

### 대시보드에 데이터 안 들어옴
1. `data/caiso_history.json` 파일 존재 확인
2. 대시보드와 같은 폴더 (또는 부모) 에 위치 확인
3. 브라우저 개발자 도구(F12) → Network 탭에서 `caiso_history.json` 요청 확인
4. file:// 사용 중이면 → http server로 변경

---

## 🗑 제거

```bash
bash uninstall_macos.sh   # macOS
bash uninstall_cron.sh    # Linux
```

---

## 📈 다음 단계

데이터가 쌓이기 시작하면:

1. **2주 후**: 알고리즘 진단 지표 활성화 → 모델 정확도 평가 시작
2. **1개월 후**: Conformal 보정이 안정적으로 자동 적용
3. **3개월 후**: 누적 비교에서 트렌드 명확 → 모델 v3 검토

매일 5분 모니터링만으로 자동으로 학습되는 트레이딩 시스템 완성!
