"""Check google-ads SDK version on VPS via SFTP + execute."""
import paramiko
import warnings
import tempfile
import os

warnings.filterwarnings("ignore")

# Script to run on VPS
REMOTE_SCRIPT = r'''
import sys, os, subprocess

sys.path.insert(0, "/root/rankpulse")

# pip version
r = subprocess.run(
    ["/root/rankpulse/venv/bin/pip", "show", "google-ads"],
    capture_output=True, text=True,
)
for line in r.stdout.strip().split("\n")[:3]:
    print(line)

# Available API versions in the SDK
import google.ads.googleads
base = os.path.dirname(google.ads.googleads.__file__)
versions = sorted([d for d in os.listdir(base) if d.startswith("v")])
print("Available API versions:", versions)

# Default version
from google.ads.googleads.client import GoogleAdsClient
c = GoogleAdsClient.load_from_dict({
    "developer_token": "test",
    "client_id": "test",
    "client_secret": "test",
    "refresh_token": "test",
    "use_proto_plus": True,
})
dv = getattr(c, "_DEFAULT_VERSION", "unknown")
print("Default version:", dv)
'''

from dotenv import load_dotenv
load_dotenv()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    os.getenv("VPS_HOST"),
    username=os.getenv("VPS_USER", "root"),
    password=os.getenv("VPS_PASSWORD"),
)

sftp = ssh.open_sftp()
sftp.open("/tmp/_check_sdk.py", "w").write(REMOTE_SCRIPT)
sftp.close()

_, stdout, stderr = ssh.exec_command(
    "cd /root/rankpulse && source venv/bin/activate && python /tmp/_check_sdk.py",
    timeout=20,
)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:500])
ssh.close()
