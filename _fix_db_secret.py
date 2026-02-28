"""Fix missing client_secret in VPS DB."""
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
s.google_ads_client_secret = "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"
s.save(update_fields=["google_ads_client_secret"])
print("client_secret saved:", bool(s.google_ads_client_secret), len(s.google_ads_client_secret))
print("google_ads_configured:", s.google_ads_configured)
"""

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("31.97.171.87", username="root", password="REDACTED")

sftp = ssh.open_sftp()
with sftp.open("/tmp/_fix_secret.py", "w") as f:
    f.write(REMOTE_SCRIPT)
sftp.close()

_, stdout, stderr = ssh.exec_command(
    "cd /root/rankpulse && source venv/bin/activate && python /tmp/_fix_secret.py",
    timeout=15,
)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("ERR:", err[:300])
ssh.close()
