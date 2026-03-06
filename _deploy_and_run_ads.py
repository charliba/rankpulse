"""Deploy ads_client.py to VPS and run campaign setup."""
import paramiko
import warnings
import os

warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

VPS_HOST = os.getenv("VPS_HOST")
VPS_USER = os.getenv("VPS_USER", "root")
VPS_PASS = os.getenv("VPS_PASSWORD")
VPS_BASE = os.getenv("VPS_PROJECT_PATH", "/root/rankpulse")

LOCAL_BASE = os.path.dirname(os.path.abspath(__file__))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
sftp = ssh.open_sftp()

# 1. Deploy updated ads_client.py
local_file = os.path.join(LOCAL_BASE, "apps", "analytics", "ads_client.py")
remote_file = f"{VPS_BASE}/apps/analytics/ads_client.py"
sftp.put(local_file, remote_file)
print(f"  OK: ads_client.py deployed")

sftp.close()

# 2. Run manage_ads commands
commands = [
    ("Google Ads Account Info", f"cd {VPS_BASE} && source venv/bin/activate && python manage.py manage_ads account 2>&1"),
    ("Listing existing campaigns", f"cd {VPS_BASE} && source venv/bin/activate && python manage.py manage_ads list 2>&1"),
    ("Setting up Beezle campaign", f"cd {VPS_BASE} && source venv/bin/activate && python manage.py manage_ads setup-beezle 2>&1"),
    ("Listing campaigns after setup", f"cd {VPS_BASE} && source venv/bin/activate && python manage.py manage_ads list 2>&1"),
    ("Listing conversion actions", f"cd {VPS_BASE} && source venv/bin/activate && python manage.py manage_ads conversions 2>&1"),
]

for label, cmd in commands:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        # Filter out INFO log lines for cleaner output
        for line in err.split("\n"):
            if "ERROR" in line or "WARNING" in line:
                print(f"  {line}")

ssh.close()
print(f"\n{'='*60}")
print("  Done!")
print(f"{'='*60}")
