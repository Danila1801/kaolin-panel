"""Claude Code hook -> one UDP datagram to kaolin_daemon.py. Stdlib only, returns instantly.

    python -I hook.py done       (Stop)
    python -I hook.py working    (UserPromptSubmit)
    python -I hook.py waiting    (Notification; only permission requests, not the idle reminder)
"""
import json
import socket
import sys

event = sys.argv[1] if len(sys.argv) > 1 else "done"

if event == "waiting":
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        data = {}
    kind = str(data.get("notification_type", "")) + " " + str(data.get("message", ""))
    if "idle" in kind.lower() or "waiting for your input" in kind.lower():
        sys.exit(0)  # "Claude is waiting for your input" comes after Stop; keep showing done/ready

try:
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(event.encode(), ("127.0.0.1", 47474))
except OSError:
    pass
