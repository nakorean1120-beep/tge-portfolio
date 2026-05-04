#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  TGE CAISO Auto Fetcher — 통합 셋업
# ═══════════════════════════════════════════════════════════
#  한 명령으로 모든 설치 + 자동 실행 등록
#
#  사용: bash setup.sh
# ═══════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  TGE CAISO Auto Fetcher v2 — 통합 셋업                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 1. Python 체크
if ! command -v python3 &> /dev/null; then
    echo "❌ python3가 필요해요"
    echo "   macOS: brew install python3"
    echo "   Ubuntu: sudo apt install python3 python3-pip"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✓ Python: $PYTHON_VERSION"

# 2. 의존성 설치
echo ""
echo "📦 의존성 설치..."
pip3 install -q -r "$SCRIPT_DIR/requirements.txt" || pip3 install -q requests schedule
echo "✓ requests, schedule 설치 완료"

# 3. 폴더 권한
mkdir -p "$SCRIPT_DIR/data"
chmod +x "$SCRIPT_DIR/caiso_fetcher.py" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/caiso_scheduler.py" 2>/dev/null || true
chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true

# 4. 첫 fetch 테스트
echo ""
echo "📡 첫 데이터 fetch 테스트..."
echo "─────────────────────────────────────────────────"
python3 "$SCRIPT_DIR/caiso_fetcher.py" || {
    echo ""
    echo "⚠ 첫 fetch 실패. 가능한 원인:"
    echo "  1. 어제 데이터 아직 미공개 (오전 11시 이후 다시 시도)"
    echo "  2. 네트워크/방화벽 차단"
    echo "  3. CAISO API 일시 장애"
    echo ""
    echo "수동 재시도: python3 $SCRIPT_DIR/caiso_fetcher.py"
}
echo "─────────────────────────────────────────────────"

# 5. OS 감지 → 자동 실행 등록
echo ""
echo "🤖 자동 실행 설정..."

OS=$(uname -s)
if [ "$OS" = "Darwin" ]; then
    echo "   macOS 감지 → launchd 등록"
    bash "$SCRIPT_DIR/install_macos.sh"
elif [ "$OS" = "Linux" ]; then
    echo "   Linux 감지 → cron 등록"
    bash "$SCRIPT_DIR/install_cron.sh"
else
    echo "   ⚠ 자동 등록 미지원 OS: $OS"
    echo "   수동: python3 $SCRIPT_DIR/caiso_scheduler.py &"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ✅ 셋업 완료!                                            ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "📋 다음 단계:"
echo ""
echo "  1. 백필 (지난 14일 채우기 - 권장):"
echo "     python3 caiso_fetcher.py --backfill 14"
echo ""
echo "  2. 대시보드를 같은 폴더로 이동:"
echo "     mv ~/Downloads/TGE_Portfolio_v5.html $(dirname $SCRIPT_DIR)/"
echo ""
echo "  3. http server로 대시보드 열기:"
echo "     cd $(dirname $SCRIPT_DIR) && python3 -m http.server 8000"
echo "     → http://localhost:8000/TGE_Portfolio_v5.html"
echo ""
echo "  4. Result 탭 → '📡 CAISO 자동 로드' 클릭"
echo ""
echo "📜 로그: tail -f $SCRIPT_DIR/caiso.log"
echo ""
