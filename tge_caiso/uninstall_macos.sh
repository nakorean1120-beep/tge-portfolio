#!/bin/bash
# TGE CAISO Fetcher 제거 (macOS launchd)

PLIST="$HOME/Library/LaunchAgents/com.tge.caiso.fetcher.plist"

if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "✅ TGE CAISO 자동 실행 제거 완료"
else
    echo "⚠ 설치된 서비스가 없어요"
fi
