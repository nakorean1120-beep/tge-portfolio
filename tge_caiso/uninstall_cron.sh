#!/bin/bash
# TGE CAISO Fetcher cron 제거

CRON_TAG="# TGE_CAISO_FETCHER"
crontab -l 2>/dev/null | grep -v "$CRON_TAG" | crontab -
echo "✅ cron 제거 완료"
echo ""
echo "현재 cron:"
crontab -l 2>/dev/null || echo "(비어있음)"
