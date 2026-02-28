"""Deploy RankPulse Google API updates to VPS."""
import os
import warnings

import paramiko
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

HOST = os.getenv("VPS_HOST", "")
USER = os.getenv("VPS_USER", "root")
PASSWORD = os.getenv("VPS_PASSWORD", "")
BASE = os.getenv("VPS_PROJECT_PATH", "/root/rankpulse")
LOCAL = os.path.dirname(os.path.abspath(__file__))

print(f"Connecting to {HOST}...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
sftp = client.open_sftp()


def ensure_remote_dir(sftp_client, path):
    dirs = path.split("/")
    current = ""
    for d in dirs:
        if not d:
            current = "/"
            continue
        current = current.rstrip("/") + "/" + d
        try:
            sftp_client.stat(current)
        except FileNotFoundError:
            sftp_client.mkdir(current)
            print(f"  mkdir {current}")


files = [
    "apps/analytics/search_console.py",
    "apps/analytics/ga4_admin.py",
    "apps/analytics/ads_client.py",
    "apps/analytics/views.py",
    "apps/analytics/urls.py",
    "apps/analytics/management/commands/fetch_gsc_data.py",
    "apps/analytics/management/commands/submit_sitemaps.py",
    "apps/analytics/management/commands/request_indexing.py",
    "apps/analytics/management/commands/mark_key_events.py",
    "apps/analytics/management/commands/manage_ads.py",
    "requirements.txt",
    "config/settings.py",
]

for f in files:
    local_path = os.path.join(LOCAL, f.replace("/", os.sep))
    remote_path = f"{BASE}/{f}"
    remote_dir = "/".join(remote_path.split("/")[:-1])
    ensure_remote_dir(sftp, remote_dir)
    try:
        sftp.put(local_path, remote_path)
        print(f"  OK: {f}")
    except Exception as e:
        print(f"  FAIL: {f} - {e}")

sftp.close()
print()

# Install new packages
cmds = [
    f"cd {BASE} && source venv/bin/activate && pip install google-analytics-data google-analytics-admin google-ads --quiet 2>&1 | tail -5",
    f"cd {BASE} && source venv/bin/activate && pip install -r requirements.txt --quiet 2>&1 | tail -5",
]

for cmd in cmds:
    print(f">>> {cmd[:70]}...")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=180)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        print(err)
    print()

# Get gunicorn PID and reload
stdin, stdout, stderr = client.exec_command("pgrep -of gunicorn.*8002")
pid = stdout.read().decode().strip()
if pid:
    client.exec_command(f"kill -HUP {pid}")
    print(f"Gunicorn reloaded (PID {pid})")
else:
    stdin, stdout, stderr = client.exec_command("systemctl restart gunicorn-rankpulse 2>&1")
    out = stdout.read().decode().strip()
    print(f"Restart: {out or 'OK'}")

client.close()
print("Deploy complete!")
