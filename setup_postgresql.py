#!/usr/bin/env python3
"""
Instala PostgreSQL no VPS, cria banco e usuário para RankPulse.
Mesma arquitetura do setup_postgresql.py do Beezle.

Uso:
    cd rankPulse
    python setup_postgresql.py
"""
import os
import secrets
import string
import sys
import warnings

import paramiko
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

HOST: str = os.getenv("VPS_HOST", "")
USER: str = os.getenv("VPS_USER", "root")
PASSWORD: str = os.getenv("VPS_PASSWORD", "")
BASE: str = os.getenv("VPS_PROJECT_PATH", "/root/rankpulse")

if not HOST or not PASSWORD:
    print("❌ ERRO: Credenciais não encontradas no .env")
    sys.exit(1)

# ── Config PostgreSQL ────────────────────────────────────────────
DB_NAME = "rankpulse"
DB_USER = "rankpulse_user"
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "") or "".join(
    secrets.choice(string.ascii_letters + string.digits) for _ in range(24)
)


def run_cmd(client: paramiko.SSHClient, cmd: str, timeout: int = 60) -> tuple[str, str]:
    """Executa comando remoto."""
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        return (
            stdout.read().decode("utf-8", errors="ignore"),
            stderr.read().decode("utf-8", errors="ignore"),
        )
    except Exception as e:
        return "", str(e)


def step(n: int, msg: str) -> None:
    print(f"\n[{n}] {msg}")
    sys.stdout.flush()


def main() -> None:
    print("=" * 60)
    print("SETUP POSTGRESQL — RankPulse")
    print("=" * 60)

    step(1, "Conectando ao VPS...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    except Exception as e:
        print(f"    ERRO: {e}")
        return
    print("    OK!")

    step(2, "Verificando PostgreSQL...")
    out, _ = run_cmd(client, "pg_isready")
    if "accepting connections" in out:
        print("    PostgreSQL já rodando ✅")
    else:
        print("    Instalando PostgreSQL...")
        run_cmd(client, "apt-get update -qq", timeout=120)
        run_cmd(client, "apt-get install -y -qq postgresql postgresql-contrib", timeout=180)
        run_cmd(client, "systemctl start postgresql")
        run_cmd(client, "systemctl enable postgresql")
        out, _ = run_cmd(client, "pg_isready")
        if "accepting connections" in out:
            print("    PostgreSQL instalado e rodando ✅")
        else:
            print("    ⚠️  PostgreSQL pode não estar rodando")

    step(3, f"Criando banco '{DB_NAME}' e usuário '{DB_USER}'...")

    # Check if exists
    out, _ = run_cmd(client, f"sudo -u postgres psql -tc \"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'\"")
    if "1" in out:
        print(f"    Banco '{DB_NAME}' já existe. Pulando criação.")
    else:
        run_cmd(client, f"sudo -u postgres psql -c \"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}';\"")
        run_cmd(client, f"sudo -u postgres psql -c \"CREATE DATABASE {DB_NAME} OWNER {DB_USER};\"")
        run_cmd(client, f"sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};\"")
        print(f"    Banco criado com sucesso ✅")

    step(4, "Atualizando .env no servidor...")
    sftp = client.open_sftp()

    # Read current .env
    env_content = ""
    try:
        with sftp.file(f"{BASE}/.env", "r") as f:
            env_content = f.read().decode()
    except Exception:
        pass

    # Update DB settings
    updates = {
        "DB_ENGINE": "postgresql",
        "DB_NAME": DB_NAME,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
    }

    for key, value in updates.items():
        if f"{key}=" in env_content:
            import re
            env_content = re.sub(f"^{key}=.*$", f"{key}={value}", env_content, flags=re.MULTILINE)
        else:
            env_content += f"\n{key}={value}"

    with sftp.file(f"{BASE}/.env", "w") as f:
        f.write(env_content)

    sftp.close()
    print("    .env atualizado ✅")

    step(5, "Rodando migrations...")
    cmd = f"cd {BASE} && source venv/bin/activate && python manage.py migrate --noinput 2>&1"
    out, err = run_cmd(client, cmd, timeout=60)
    print(f"    {out.strip()[-200:] if out else 'OK'}")

    step(6, "Criando superuser...")
    cmd = (
        f"cd {BASE} && source venv/bin/activate && "
        f"python manage.py shell -c \""
        f"from django.contrib.auth import get_user_model; "
        f"User = get_user_model(); "
        f"User.objects.filter(username='admin').exists() or "
        f"User.objects.create_superuser('admin', 'admin@{os.getenv('APP_DOMAIN', 'rankpulse.cloud')}', 'changeme123')"
        f"\" 2>&1"
    )
    out, _ = run_cmd(client, cmd, timeout=30)
    print("    Superuser criado (admin / changeme123) — TROQUE A SENHA!")

    client.close()
    print("\n" + "=" * 60)
    print("SETUP POSTGRESQL CONCLUÍDO")
    print("=" * 60)
    print(f"\nCredenciais:")
    print(f"  Banco: {DB_NAME}")
    print(f"  Usuário: {DB_USER}")
    print(f"  Senha: {DB_PASSWORD}")
    print(f"\n⚠️  Guarde a senha do banco! Ela foi salva no .env do servidor.")


if __name__ == "__main__":
    main()
