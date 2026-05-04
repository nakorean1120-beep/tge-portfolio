#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  TGE CAISO Auto Scheduler — macOS launchd 설치
# ═══════════════════════════════════════════════════════════
#  - 시스템 부팅 시 자동 시작
#  - 매일 11:00 + 14:00 자동 실행
#  - 실패 시 자동 재시작
#
#  설치: bash install_macos.sh
#  제거: bash uninstall_macos.sh
# ═══════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(which python3)"
FETCHER="$SCRIPT_DIR/caiso_fetcher.py"
PLIST="$HOME/Library/LaunchAgents/com.tge.caiso.fetcher.plist"

echo "═══════════════════════════════════════════════════════════"
echo "  TGE CAISO Fetcher — macOS launchd 설치"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  스크립트: $FETCHER"
echo "  Python:  $PYTHON_BIN"
echo "  PLIST:   $PLIST"
echo ""

# 1. 의존성 체크
if ! command -v python3 &> /dev/null; then
    echo "❌ python3가 설치되지 않았어요."
    echo "   brew install python3"
    exit 1
fi

# 2. requests 설치 확인
if ! python3 -c "import requests" &> /dev/null; then
    echo "📦 requests 라이브러리 설치 중..."
    pip3 install requests
fi

# 3. data 폴더 생성
mkdir -p "$SCRIPT_DIR/data"

# 4. 실행 권한
chmod +x "$FETCHER"

# 5. plist 파일 생성 (매일 11:00 + 14:00)
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tge.caiso.fetcher</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$FETCHER</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>

    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>11</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>14</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>

    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/caiso.log</string>

    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/caiso_error.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

echo "✅ plist 파일 생성: $PLIST"
echo ""

# 6. 기존 service 언로드 (재설치 시)
launchctl unload "$PLIST" 2>/dev/null || true

# 7. 새 service 로드
launchctl load "$PLIST"

echo "✅ launchd 서비스 등록 완료"
echo ""
echo "다음 실행 시각:"
echo "  매일 오전 11:00 (1차)"
echo "  매일 오후 14:00 (재시도)"
echo ""
echo "📊 즉시 1회 테스트 실행:"
echo "   python3 $FETCHER"
echo ""
echo "📋 상태 확인:"
echo "   launchctl list | grep tge.caiso"
echo ""
echo "📜 로그 확인:"
echo "   tail -f $SCRIPT_DIR/caiso.log"
echo ""
echo "🗑 제거:"
echo "   bash uninstall_macos.sh"
echo ""
