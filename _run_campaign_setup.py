"""Deploy .env + run Beezle campaign setup + SEO audit on VPS."""
from __future__ import annotations

import os
import paramiko
import warnings

warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

VPS_HOST = os.getenv("VPS_HOST")
VPS_USER = os.getenv("VPS_USER", "root")
VPS_PASS = os.getenv("VPS_PASSWORD")
REMOTE_BASE = os.getenv("VPS_PROJECT_PATH", "/root/rankpulse")
VENV_PY = f"{REMOTE_BASE}/venv/bin/python"
LOCAL_BASE = os.path.dirname(os.path.abspath(__file__))


def run(ssh, cmd: str, label: str = "") -> str:
    """Run command via SSH and print output."""
    if label:
        print(f"\n► {label}")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err and "WARNING" not in err.upper():
        print(f"  STDERR: {err[-500:]}")
    return out


def main() -> None:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
    sftp = ssh.open_sftp()

    # 1. Upload .env with Google Ads credentials
    local_env = os.path.join(LOCAL_BASE, ".env")
    remote_env = f"{REMOTE_BASE}/.env"
    print(f"  UPLOAD .env → {remote_env}")
    sftp.put(local_env, remote_env)
    sftp.close()

    # 2. Check if google-ads is installed
    run(ssh,
        f"{REMOTE_BASE}/venv/bin/pip install google-ads 2>&1 | tail -3",
        "Installing google-ads SDK (if needed)...")

    # 3. Check account info first
    run(ssh,
        f"cd {REMOTE_BASE} && {VENV_PY} manage.py manage_ads account",
        "Google Ads Account Info...")

    # 4. List existing campaigns
    run(ssh,
        f"cd {REMOTE_BASE} && {VENV_PY} manage.py manage_ads list",
        "Listing existing campaigns...")

    # 5. Run setup-beezle to create full campaign
    run(ssh,
        f"cd {REMOTE_BASE} && {VENV_PY} manage.py manage_ads setup-beezle",
        "Creating Beezle campaign (campaign + ad groups + keywords + ads + conversions)...")

    # 6. List campaigns again to confirm
    run(ssh,
        f"cd {REMOTE_BASE} && {VENV_PY} manage.py manage_ads list",
        "Confirming campaigns created...")

    # 7. List conversions
    run(ssh,
        f"cd {REMOTE_BASE} && {VENV_PY} manage.py manage_ads conversions",
        "Listing conversion actions...")

    ssh.close()
    print("\n🚀 Done! Campaign setup complete.")


if __name__ == "__main__":
    main()
