"""Verify RankPulse deployment — check server + imports."""
import os
import warnings

import paramiko
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    os.getenv("VPS_HOST"),
    username="root",
    password=os.getenv("VPS_PASSWORD"),
    timeout=30,
)

cmds = [
    "curl -s -o /dev/null -w '%{http_code}' http://localhost:8002/",
    "cd /root/rankpulse && source venv/bin/activate && python -c 'from apps.analytics.ga4_admin import GA4AdminClient; print(\"GA4 Admin OK\")'",
    "cd /root/rankpulse && source venv/bin/activate && python -c 'from apps.analytics.ads_client import GoogleAdsManager; print(\"Ads Client OK\")'",
    "cd /root/rankpulse && source venv/bin/activate && python -c 'from apps.analytics.search_console import SearchConsoleClient; print(\"GSC Client OK\")'",
    "cd /root/rankpulse && source venv/bin/activate && python manage.py showmigrations analytics 2>&1 | head -10",
]

for cmd in cmds:
    print(f">>> {cmd[:65]}...")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(f"  {out}")
    if err:
        print(f"  {err}")
    print()

client.close()
print("Verification complete!")
