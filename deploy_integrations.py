"""Deploy RankPulse integrations page to VPS.

Files: models.py, forms.py, views.py, urls.py, sidebar.html,
       site_detail.html, site_integrations.html, analytics/views.py,
       migration 0003.
Then: migrate + reload Gunicorn.
"""
from __future__ import annotations

import os
import paramiko

VPS_HOST = "31.97.171.87"
VPS_USER = "root"
VPS_PASS = "REDACTED"
REMOTE_BASE = "/root/rankpulse"
GUNICORN_PID = 377553

LOCAL_BASE = os.path.dirname(os.path.abspath(__file__))

FILES = [
    # Core app
    ("apps/core/models.py", f"{REMOTE_BASE}/apps/core/models.py"),
    ("apps/core/forms.py", f"{REMOTE_BASE}/apps/core/forms.py"),
    ("apps/core/views.py", f"{REMOTE_BASE}/apps/core/views.py"),
    ("apps/core/urls.py", f"{REMOTE_BASE}/apps/core/urls.py"),
    # Migration
    (
        "apps/core/migrations/0003_site_google_ads_service_accounts.py",
        f"{REMOTE_BASE}/apps/core/migrations/0003_site_google_ads_service_accounts.py",
    ),
    # Analytics view (updated _get_ads_manager)
    ("apps/analytics/views.py", f"{REMOTE_BASE}/apps/analytics/views.py"),
    # Templates
    ("templates/components/sidebar.html", f"{REMOTE_BASE}/templates/components/sidebar.html"),
    ("templates/core/site_detail.html", f"{REMOTE_BASE}/templates/core/site_detail.html"),
    ("templates/core/site_integrations.html", f"{REMOTE_BASE}/templates/core/site_integrations.html"),
]


def main() -> None:
    """Upload files, run migration, reload Gunicorn."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
    sftp = ssh.open_sftp()

    # ── Upload files ────────────────────────────────
    for local_rel, remote_path in FILES:
        local_path = os.path.join(LOCAL_BASE, local_rel)
        print(f"  UPLOAD  {local_rel}  →  {remote_path}")
        sftp.put(local_path, remote_path)

    sftp.close()
    print(f"\n✓ {len(FILES)} files uploaded")

    # ── Run migration ───────────────────────────────
    print("\n► Running migrate …")
    _, stdout, stderr = ssh.exec_command(
        f"cd {REMOTE_BASE} && /root/rankpulse/venv/bin/python manage.py migrate core"
    )
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(f"  STDERR: {err}")

    # ── Reload Gunicorn ─────────────────────────────
    print(f"\n► Reloading Gunicorn (PID {GUNICORN_PID}) …")
    _, stdout, stderr = ssh.exec_command(f"kill -HUP {GUNICORN_PID}")
    err = stderr.read().decode()
    if err:
        # PID might have changed — find current
        print(f"  HUP failed ({err.strip()}), trying pgrep …")
        _, stdout, _ = ssh.exec_command("pgrep -f 'gunicorn.*rankpulse'")
        pids = stdout.read().decode().strip().split("\n")
        if pids and pids[0]:
            master = pids[0]
            print(f"  Found master PID {master}, sending HUP …")
            ssh.exec_command(f"kill -HUP {master}")
        else:
            print("  ⚠ Could not find Gunicorn process!")
    print("✓ Gunicorn reloaded")

    ssh.close()
    print("\n🚀 Deploy complete — rankpulse.cloud/site/<id>/integrations/")


if __name__ == "__main__":
    main()
