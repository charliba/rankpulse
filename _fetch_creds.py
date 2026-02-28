"""Fetch Google Ads credentials from RankPulse VPS database."""
import paramiko
import warnings

warnings.filterwarnings("ignore")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("31.97.171.87", username="root", password="REDACTED")

script = r"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import sys
sys.path.insert(0, '/root/rankpulse')
django.setup()
from apps.core.models import Site
for s in Site.objects.all():
    print(f'SITE|{s.pk}|{s.name}')
    print(f'CLIENT_ID|{s.google_ads_client_id}')
    print(f'CLIENT_SECRET|{s.google_ads_client_secret}')
    print(f'CUSTOMER_ID|{s.google_ads_customer_id}')
    print(f'DEV_TOKEN|{s.google_ads_developer_token}')
    print(f'REFRESH|{s.google_ads_refresh_token}')
    print(f'LOGIN_CID|{s.google_ads_login_customer_id}')
"""

cmd = f'cd /root/rankpulse && /root/rankpulse/venv/bin/python -c "{script}"'
_, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("ERR:", err[-500:])
ssh.close()
