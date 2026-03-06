#!/usr/bin/env python3
"""
Generate SSL certificate for rankpulse.cloud via certbot.
Mesma estrutura do _setup_ssl.py do Beezle.

Uso:
    cd rankPulse
    python _setup_ssl.py
"""
import os
import time

import paramiko
from dotenv import load_dotenv

load_dotenv()

HOST: str = os.getenv("VPS_HOST", "")
PASSWORD: str = os.getenv("VPS_PASSWORD", "")
DOMAIN: str = os.getenv("APP_DOMAIN", "rankpulse.cloud")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username="root", password=PASSWORD, timeout=30)


def run(cmd: str, t: int = 120) -> tuple[str, str]:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=t)
    return (
        stdout.read().decode("utf-8", "ignore").strip(),
        stderr.read().decode("utf-8", "ignore").strip(),
    )


# Check certbot
print("=== CHECKING CERTBOT ===")
out, _ = run("which certbot 2>&1")
print(f"  certbot: {out}")

if not out or "not found" in out:
    print("  Installing certbot...")
    run("apt-get update && apt-get install -y certbot python3-certbot-nginx 2>&1", t=120)
    out, _ = run("which certbot 2>&1")
    print(f"  certbot installed: {out}")

# Check DNS
print("\n=== CHECKING DNS ===")
out, _ = run(f"dig +short {DOMAIN} A 2>&1")
print(f"  {DOMAIN} A: {out}")
out, _ = run(f"dig +short www.{DOMAIN} 2>&1")
print(f"  www.{DOMAIN}: {out}")

# Generate certificate
print("\n=== GENERATING SSL CERTIFICATE ===")
out, err = run(
    f"certbot --nginx -d {DOMAIN} -d www.{DOMAIN} "
    f"--non-interactive --agree-tos --email admin@{DOMAIN} "
    f"--redirect 2>&1",
    t=120,
)
combined = f"{out}\n{err}".strip()
print(combined[-500:])

# Verify
print("\n=== VERIFYING SSL ===")
out, _ = run("certbot certificates 2>&1")
print(out[-400:] if out else "No output")

# Reload nginx
run("systemctl reload nginx")

# Test HTTPS
print("\n=== TESTING HTTPS ===")
time.sleep(3)
out, _ = run(f"curl -s -w '|%{{http_code}}' -o /dev/null https://{DOMAIN}/ 2>&1")
print(f"  HTTPS {DOMAIN}: {out}")
out, _ = run(f"curl -s -w '|%{{http_code}}' -o /dev/null https://www.{DOMAIN}/ 2>&1")
print(f"  HTTPS www.{DOMAIN}: {out}")

client.close()
print("\n=== SSL SETUP DONE ===")
