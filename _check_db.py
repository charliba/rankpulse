"""Check DB data for Google Ads on VPS."""
import paramiko
import warnings

warnings.filterwarnings("ignore")

REMOTE_SCRIPT = """
import django, os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, "/root/rankpulse")
django.setup()
from apps.core.models import Site
s = Site.objects.get(pk=1)
print("customer_id:", repr(s.google_ads_customer_id))
print("developer_token:", bool(s.google_ads_developer_token), len(s.google_ads_developer_token or ""))
print("client_id:", bool(s.google_ads_client_id), len(s.google_ads_client_id or ""))
print("client_secret:", bool(s.google_ads_client_secret), len(s.google_ads_client_secret or ""))
print("refresh_token:", bool(s.google_ads_refresh_token), len(s.google_ads_refresh_token or ""))
print("login_customer_id:", repr(s.google_ads_login_customer_id))
print()
print("google_ads_configured:", s.google_ads_configured)
"""

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("31.97.171.87", username="root", password="REDACTED")

sftp = ssh.open_sftp()
with sftp.open("/tmp/_check_db.py", "w") as f:
    f.write(REMOTE_SCRIPT)
sftp.close()

_, stdout, stderr = ssh.exec_command(
    "cd /root/rankpulse && source venv/bin/activate && python /tmp/_check_db.py",
    timeout=15,
)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("ERR:", err[:300])
ssh.close()
