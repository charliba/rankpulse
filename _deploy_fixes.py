"""Deploy forms.py and ads_client.py fixes to VPS, then reload gunicorn."""
import os
import paramiko
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

LOCAL_BASE = os.path.dirname(os.path.abspath(__file__))
VPS_BASE = os.getenv("VPS_PROJECT_PATH", "/root/rankpulse")

FILES = [
    ("apps/core/forms.py", "apps/core/forms.py"),
    ("apps/analytics/ads_client.py", "apps/analytics/ads_client.py"),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    os.getenv("VPS_HOST"),
    username=os.getenv("VPS_USER", "root"),
    password=os.getenv("VPS_PASSWORD"),
)
sftp = ssh.open_sftp()

for local_rel, remote_rel in FILES:
    local_path = os.path.join(LOCAL_BASE, local_rel.replace("/", os.sep))
    remote_path = f"{VPS_BASE}/{remote_rel}"
    sftp.put(local_path, remote_path)
    print(f"  OK: {remote_rel}")

sftp.close()

# Reload gunicorn
_, stdout, stderr = ssh.exec_command(
    "kill -HUP $(cat /tmp/rankpulse_gunicorn.pid 2>/dev/null || pgrep -f 'gunicorn.*8002' | head -1) 2>&1 && echo 'Gunicorn reloaded' || echo 'Reload attempted'",
    timeout=10,
)
print(stdout.read().decode().strip())

ssh.close()
print("Deploy complete!")
