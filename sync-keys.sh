#!/bin/bash
# sync-keys.sh — Синхронизирует ключи с VPS в локальный .env
VPS_HOST="77.110.126.107"
VPS_USER="root"
VPS_PASS="3wvieZOZ5EdV"
LOCAL_ENV="$(dirname "$0")/.env"
echo "Синхронизация ключей с VPS..."
python3 - <<PYEOF
import sys, subprocess
try:
    import paramiko
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("77.110.126.107", username="root", password="3wvieZOZ5EdV", timeout=10)
_, stdout, _ = client.exec_command("cat /etc/jarvis-secrets")
content = stdout.read().decode()
client.close()
lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#") and "=" in l]
with open("", "w") as f:
    f.write("
".join(lines) + "
")
print("
.env обновлён:")
[print(f"  {l.split(chr(61))[0]}=***") for l in lines]
PYEOF

