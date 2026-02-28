"""Save LOGIN_CUSTOMER_ID (MCC) to VPS DB and .env."""
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
s.google_ads_login_customer_id = "259-958-1821"
s.save(update_fields=["google_ads_login_customer_id"])
print("login_customer_id saved:", s.google_ads_login_customer_id)
print("google_ads_configured:", s.google_ads_configured)
"""

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("31.97.171.87", username="root", password="REDACTED")

sftp = ssh.open_sftp()
with sftp.open("/tmp/_save_mcc.py", "w") as f:
    f.write(REMOTE_SCRIPT)
sftp.close()

# Save to DB
_, stdout, stderr = ssh.exec_command(
    "cd /root/rankpulse && source venv/bin/activate && python /tmp/_save_mcc.py",
    timeout=15,
)
print(stdout.read().decode().strip())

# Update .env on VPS
_, stdout2, _ = ssh.exec_command(
    "cd /root/rankpulse && "
    "grep -q GOOGLE_ADS_LOGIN_CUSTOMER_ID .env && "
    "sed -i 's/^GOOGLE_ADS_LOGIN_CUSTOMER_ID=.*/GOOGLE_ADS_LOGIN_CUSTOMER_ID=259-958-1821/' .env || "
    "echo 'GOOGLE_ADS_LOGIN_CUSTOMER_ID=259-958-1821' >> .env && "
    "echo 'VPS .env updated'",
    timeout=10,
)
print(stdout2.read().decode().strip())

ssh.close()
print("Done!")
