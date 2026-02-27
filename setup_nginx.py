#!/usr/bin/env python3
"""
Configure Nginx for rankpulse.cloud on the VPS.
Creates the Nginx server block and enables the site.

Uso:
    cd trafic_provider
    python setup_nginx.py
"""
import os
import sys

import paramiko
from dotenv import load_dotenv

load_dotenv()

HOST: str = os.getenv("VPS_HOST", "")
PASSWORD: str = os.getenv("VPS_PASSWORD", "")
DOMAIN: str = os.getenv("APP_DOMAIN", "rankpulse.cloud")
GUNICORN_PORT: str = os.getenv("GUNICORN_PORT", "8002")
BASE: str = os.getenv("VPS_PROJECT_PATH", "/root/rankpulse")

if not HOST or not PASSWORD:
    print("❌ Credenciais não encontradas no .env")
    sys.exit(1)

NGINX_CONF = f"""server {{
    listen 80;
    server_name {DOMAIN} www.{DOMAIN};

    location /static/ {{
        alias {BASE}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }}

    location / {{
        proxy_pass http://127.0.0.1:{GUNICORN_PORT};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username="root", password=PASSWORD, timeout=30)


def run(cmd: str, timeout: int = 30) -> tuple[str, str]:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode().strip(), stderr.read().decode().strip()


print("=" * 50)
print(f"SETUP NGINX — {DOMAIN}")
print("=" * 50)

# 1. Write Nginx config
print("\n[1] Criando configuração Nginx...")
sftp = client.open_sftp()
conf_path = f"/etc/nginx/sites-available/{DOMAIN}"
with sftp.file(conf_path, "w") as f:
    f.write(NGINX_CONF)
sftp.close()
print(f"    Escrito: {conf_path}")

# 2. Enable site
print("\n[2] Habilitando site...")
run(f"ln -sf {conf_path} /etc/nginx/sites-enabled/{DOMAIN}")
print("    Symlink criado")

# 3. Test Nginx config
print("\n[3] Testando configuração...")
out, err = run("nginx -t 2>&1")
combined = f"{out} {err}"
if "successful" in combined:
    print("    nginx -t: OK ✅")
else:
    print(f"    nginx -t: FALHA\n    {combined[:300]}")
    client.close()
    sys.exit(1)

# 4. Reload Nginx
print("\n[4] Recarregando Nginx...")
run("systemctl reload nginx")
print("    OK")

# 5. Create staticfiles dir
print("\n[5] Criando diretórios...")
run(f"mkdir -p {BASE}/staticfiles")
run(f"mkdir -p {BASE}/logs")
print("    OK")

# 6. Test
print(f"\n[6] Teste HTTP...")
out, _ = run(f"curl -s -o /dev/null -w '%{{http_code}}' http://{DOMAIN}/ 2>/dev/null || echo 'timeout'")
print(f"    http://{DOMAIN}: {out}")

client.close()

print("\n" + "=" * 50)
print("NGINX CONFIGURADO")
print("=" * 50)
print(f"\nPróximo passo: python _setup_ssl.py  (para HTTPS)")
