#!/usr/bin/env python3
"""
Verify RankPulse site is running correctly.
Mesma estrutura do verify_site.py / check_server.py do Beezle.

Uso:
    cd trafic_provider
    python verify_site.py
"""
import os
import sys

import paramiko
from dotenv import load_dotenv

load_dotenv()

HOST: str = os.getenv("VPS_HOST", "")
PASSWORD: str = os.getenv("VPS_PASSWORD", "")
BASE: str = os.getenv("VPS_PROJECT_PATH", "/root/rankpulse")
GUNICORN_PORT: str = os.getenv("GUNICORN_PORT", "8002")
DOMAIN: str = os.getenv("APP_DOMAIN", "rankpulse.cloud")

if not HOST or not PASSWORD:
    print("❌ Credenciais não encontradas no .env")
    sys.exit(1)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username="root", password=PASSWORD, timeout=30)


def run(cmd: str, timeout: int = 30) -> str:
    _, stdout, _ = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode().strip()


print("=" * 50)
print("VERIFICAÇÃO RANKPULSE")
print("=" * 50)

# 1. Gunicorn
print("\n[1] Gunicorn...")
procs = run(f"ps aux | grep 'gunicorn.*{GUNICORN_PORT}' | grep -v grep | wc -l")
print(f"    Processos: {procs}")
port_check = run(f"netstat -tlnp | grep {GUNICORN_PORT}")
print(f"    Porta {GUNICORN_PORT}: {'OK' if GUNICORN_PORT in port_check else 'FALHA'}")

# 2. Nginx
print("\n[2] Nginx...")
nginx_status = run("systemctl is-active nginx")
print(f"    Status: {nginx_status}")
nginx_conf = run(f"nginx -T 2>&1 | grep -c '{DOMAIN}'")
print(f"    Config '{DOMAIN}': {'OK' if int(nginx_conf or '0') > 0 else 'NÃO ENCONTRADO'}")

# 3. HTTP local
print("\n[3] HTTP local...")
out = run(f"curl -s -w '|%{{http_code}}' -o /dev/null http://127.0.0.1:{GUNICORN_PORT}/")
print(f"    Resposta: {out}")

# 4. HTTPS externo
print("\n[4] HTTPS externo...")
out = run(f"curl -s -o /dev/null -w '%{{http_code}}' https://{DOMAIN}/ 2>/dev/null || echo 'timeout'")
print(f"    https://{DOMAIN}: {out}")
out = run(f"curl -s -o /dev/null -w '%{{http_code}}' https://www.{DOMAIN}/ 2>/dev/null || echo 'timeout'")
print(f"    https://www.{DOMAIN}: {out}")

# 5. SSL
print("\n[5] SSL Certificate...")
out = run(f"certbot certificates 2>&1 | grep -A5 '{DOMAIN}'")
print(f"    {out[:200] if out else 'Sem certificado'}")

# 6. Database
print("\n[6] Database...")
out = run("pg_isready")
print(f"    PostgreSQL: {out}")

# 7. Disk / Memory
print("\n[7] Recursos...")
out = run("df -h / | tail -1 | awk '{print $3\"/\"$2\" (\"$5\" usado)\"}'")
print(f"    Disco: {out}")
out = run("free -h | grep Mem | awk '{print $3\"/\"$2}'")
print(f"    Memória: {out}")

client.close()
print("\n" + "=" * 50)
print("VERIFICAÇÃO CONCLUÍDA")
print("=" * 50)
