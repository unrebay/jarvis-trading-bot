#!/usr/bin/env python3
# sync-keys.py — Syncs secrets from VPS to local .env
import sys, os, subprocess

try:
    import paramiko
except ImportError:
    print("Installing paramiko...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "paramiko", "-q",
        "--break-system-packages"
    ])
    import paramiko

VPS_HOST = "77.110.126.107"
VPS_USER = "root"
VPS_PASS = "3wvieZOZ5EdV"
LOCAL_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

print("Syncing keys from VPS...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=10)
    _, stdout, _ = client.exec_command("cat /etc/jarvis-secrets")
    content = stdout.read().decode()
    client.close()
except Exception as e:
    print("Connection failed:", e)
    sys.exit(1)

lines = [
    line.strip() for line in content.splitlines()
    if line.strip() and not line.strip().startswith("#") and "=" in line
]

with open(LOCAL_ENV, "w") as f:
    f.write("\n".join(lines) + "\n")

print(".env updated:")
for line in lines:
    print("  " + line.split("=")[0] + "=***")
print("Done!")
