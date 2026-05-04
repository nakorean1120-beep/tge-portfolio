#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  TGE CAISO Auto Scheduler — Linux cron 설치
# ═══════════════════════════════════════════════════════════
#  설치: bash install_cron.sh
#  제거: bash uninstall_cron.sh
# ═══════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(which python3)"
FETCHER="$SCRIPT_DIR/caiso_fetcher.py"
LOG="$SCRIPT_DIR/caiso.log"
CRON_TAG="# TGE_CAISO_FETCHER"

echo "═══════════════════════════════════════════════════════════"
echo "  TGE CAISO Fetcher — Linux cron 설치"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 의존성
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 미설치"
    exit 1
fi

if ! python3 -c "import requests" &> /dev/null; then
    echo "📦 requests 설치 중..."
    pip3 install requests
fi

# data 폴더
mkdir -p "$SCRIPT_DIR/data"
chmod +x "$FETCHER"

# 기존 항목 제거 후 새로 추가
(crontab -l 2>/dev/null | grep -v "$CRON_TAG"; \
 echo "0 11 * * * $PYTHON_BIN $FETCHER >> $LOG 2>&1 $CRON_TAG"; \
 echo "0 14 * * * $PYTHON_BIN $FETCHER >> $LOG 2>&1 $CRON_TAG") | crontab -

echo "✅ cron 등록 완료"
echo ""
echo "현재 cron:"
crontab -l | grep TGE_CAISO || echo "(없음)"
echo ""
echo "📊 즉시 1회 테스트:"
echo "   python3 $FETCHER"
echo ""
echo "📜 로그:"
echo "   tail -f $LOG"
echo ""
echo "🗑 제거:"
echo "   bash uninstall_cron.sh"
echo ""
