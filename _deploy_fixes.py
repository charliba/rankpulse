"""Deploy forms.py and ads_client.py fixes to VPS, then reload gunicorn."""
import paramiko
import warnings
import os

warnings.filterwarnings("ignore")

LOCAL_BASE = r"c:\Users\mende\OneDrive\Profissional\python\VPS_Hostinger_31.97.171.87\rankPulse"
VPS_BASE = "/root/rankpulse"

FILES = [
    ("apps/core/forms.py", "apps/core/forms.py"),
    ("apps/analytics/ads_client.py", "apps/analytics/ads_client.py"),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("31.97.171.87", username="root", password="REDACTED")
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
