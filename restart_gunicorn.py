#!/usr/bin/env python3
"""
Restart Gunicorn on server — RankPulse
Mesma estrutura do restart_gunicorn.py do Beezle.

Uso:
    cd trafic_provider
    python restart_gunicorn.py
"""
import os
import time

import paramiko
from dotenv import load_dotenv

load_dotenv()

HOST: str = os.getenv("VPS_HOST", "")
USER: str = os.getenv("VPS_USER", "root")
PASSWORD: str = os.getenv("VPS_PASSWORD", "")
BASE: str = os.getenv("VPS_PROJECT_PATH", "/root/rankpulse")
GUNICORN_PORT: str = os.getenv("GUNICORN_PORT", "8002")
DOMAIN: str = os.getenv("APP_DOMAIN", "rankpulse.cloud")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)


def run(cmd: str, timeout: int = 30) -> tuple[str, str]:
    """Executa comando remoto."""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode().strip(), stderr.read().decode().strip()


# 1. Kill existing gunicorn
print("1. Parando Gunicorn (RankPulse)...")
run(f"pkill -f 'gunicorn.*config.wsgi.*{GUNICORN_PORT}'", timeout=10)
time.sleep(2)

# 2. Start Gunicorn
print("2. Iniciando Gunicorn...")
cmd = (
    f"cd {BASE} && source venv/bin/activate && "
    f"gunicorn config.wsgi:application "
    f"--bind=127.0.0.1:{GUNICORN_PORT} "
    f"--workers=2 --daemon "
    f"--access-logfile={BASE}/logs/access.log "
    f"--error-logfile={BASE}/logs/error.log"
)
out, err = run(cmd, timeout=15)
if out:
    print(f"   STDOUT: {out}")
if err:
    print(f"   STDERR: {err}")
time.sleep(3)

# 3. Verify
print("3. Verificando processos...")
out, _ = run(f"ps aux | grep 'gunicorn.*{GUNICORN_PORT}' | grep -v grep | wc -l")
print(f"   Processos Gunicorn: {out}")

out, _ = run(f"netstat -tlnp | grep {GUNICORN_PORT}")
if GUNICORN_PORT in out:
    print(f"   Porta {GUNICORN_PORT}: OK")
else:
    print(f"   Porta {GUNICORN_PORT}: FALHA")

# 4. Health check
print("4. Health check...")
out, _ = run(f"curl -s -w '|%{{http_code}}' -o /dev/null http://127.0.0.1:{GUNICORN_PORT}/")
print(f"   Resposta: {out}")

# 5. External test
print(f"5. Teste externo (https://{DOMAIN}/)...")
out, _ = run(f"curl -s -o /dev/null -w '%{{http_code}}' https://{DOMAIN}/ 2>/dev/null || echo 'timeout'", timeout=10)
print(f"   HTTPS Status: {out}")

ssh.close()
print("\nDone!")
