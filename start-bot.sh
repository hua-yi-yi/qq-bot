#!/usr/bin/env bash
# QQ 机器人快捷控制脚本
#   ./start-bot.sh start|stop|restart|status|log
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
SVC=qqbot.service
case "${1:-start}" in
  start)   systemctl --user start   "$SVC" && systemctl --user --no-pager status "$SVC" | head -5 ;;
  stop)    systemctl --user stop    "$SVC" && echo "stopped" ;;
  restart) systemctl --user restart "$SVC" && echo "restarted" ;;
  status)  systemctl --user --no-pager status "$SVC" | head -12 ;;
  log)     tail -f "$ROOT/logs/bot.log" ;;
  *)       echo "用法: $0 {start|stop|restart|status|log}"; exit 1 ;;
esac
