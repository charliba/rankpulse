#!/usr/bin/env python3
"""
Deploy completo via SSH — RankPulse
Mesma arquitetura do deploy.py do Beezle (Paramiko + SFTP + backup).

Uso:
    cd rankPulse
    python scripts/deploy.py
"""
import os
import subprocess
import sys
import time
import warnings
from datetime import datetime

import paramiko
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

# ── Credenciais do .env (NUNCA hardcode!) ────────────────────────
HOST: str = os.getenv("VPS_HOST", "")
USER: str = os.getenv("VPS_USER", "root")
PASSWORD: str = os.getenv("VPS_PASSWORD", "")
BASE: str = os.getenv("VPS_PROJECT_PATH", "/root/rankpulse")
GITHUB_REPO: str = os.getenv("GITHUB_REPO", "")
DOMAIN: str = os.getenv("APP_DOMAIN", "rankpulse.cloud")
GUNICORN_PORT: str = os.getenv("GUNICORN_PORT", "8002")

# Flag para resetar o banco (usar apenas quando houver mudanças destrutivas de schema)
RESET_DB: bool = "--reset-db" in sys.argv

# Validação de segurança
if not HOST or not PASSWORD:
    print("❌ ERRO: Credenciais não encontradas!")
    print("   Configure VPS_HOST e VPS_PASSWORD no arquivo .env")
    sys.exit(1)


def run_cmd(client: paramiko.SSHClient, cmd: str, timeout: int = 30) -> tuple[str, str]:
    """Executa comando remoto com timeout."""
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return out, err
    except Exception as e:
        return "", str(e)


def upload_dir(sftp: paramiko.SFTPClient, local_dir: str, remote_dir: str, base_local: str = "") -> list[str]:
    """Upload recursivo de diretório."""
    files_uploaded: list[str] = []

    try:
        sftp.mkdir(remote_dir)
    except Exception:
        pass

    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = f"{remote_dir}/{item}"
        rel_path = os.path.join(base_local, item) if base_local else item

        if os.path.isdir(local_path):
            if item in ("__pycache__", ".git", "venv", "node_modules", "staticfiles", "logs"):
                continue
            files_uploaded.extend(upload_dir(sftp, local_path, remote_path, rel_path))
        else:
            if item.endswith((".pyc", ".pyo", ".sqlite3")):
                continue
            try:
                sftp.put(local_path, remote_path)
                files_uploaded.append(rel_path)
            except Exception as e:
                print(f"    ERRO {rel_path}: {e}")

    return files_uploaded


def main() -> None:
    print("=" * 60)
    print("DEPLOY RANKPULSE")
    print(f"Servidor: {HOST} | Domínio: {DOMAIN}")
    if RESET_DB:
        print("⚠️  MODO RESET DB ATIVADO — banco será recriado do zero")
    print("=" * 60)
    sys.stdout.flush()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── 1. Conectar ──────────────────────────────────────────────
    print("\n[1] Conectando ao VPS...")
    sys.stdout.flush()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    except Exception as e:
        print(f"    ERRO: {e}")
        return
    sftp = client.open_sftp()
    print("    OK!")
    sys.stdout.flush()

    # ── 1.5 Backup do banco ─────────────────────────────────────
    print("\n[1.5] Backup do banco de dados...")
    sys.stdout.flush()
    run_cmd(client, f"mkdir -p {BASE}/backups/db")
    run_cmd(client, f"mkdir -p {BASE}/backups/code")

    db_engine_out, _ = run_cmd(client, f"grep -oP '(?<=DB_ENGINE=).*' {BASE}/.env 2>/dev/null")
    db_engine = db_engine_out.strip()
    if "postgresql" in db_engine:
        db_name_out, _ = run_cmd(client, f"grep -oP '(?<=DB_NAME=).*' {BASE}/.env 2>/dev/null")
        db_name = db_name_out.strip() or "rankpulse"
        run_cmd(
            client,
            f"sudo -u postgres pg_dump {db_name} > {BASE}/backups/db/db_{timestamp}.sql 2>/dev/null || echo 'sem banco'",
            timeout=120,
        )
        run_cmd(client, f"cd {BASE}/backups/db && ls -t *.sql 2>/dev/null | tail -n +11 | xargs -r rm")
        print(f"    Backup DB (PostgreSQL): db_{timestamp}.sql")
    else:
        run_cmd(
            client,
            f"cp {BASE}/db.sqlite3 {BASE}/backups/db/db_{timestamp}.sqlite3 2>/dev/null || echo 'sem banco'",
        )
        run_cmd(client, f"cd {BASE}/backups/db && ls -t *.sqlite3 2>/dev/null | tail -n +11 | xargs -r rm")
        print(f"    Backup DB (SQLite): db_{timestamp}.sqlite3")
    sys.stdout.flush()

    # ── 1.6 Backup do código ────────────────────────────────────
    print("\n[1.6] Backup do código atual...")
    sys.stdout.flush()
    run_cmd(
        client,
        f"cd /root && tar -czf {BASE}/backups/code/code_{timestamp}.tar.gz "
        f"--exclude='backups' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' "
        f"rankpulse/ 2>/dev/null || echo 'primeiro deploy'",
        timeout=120,
    )
    run_cmd(client, f"cd {BASE}/backups/code && ls -t *.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm")
    print(f"    Backup Code: code_{timestamp}.tar.gz")
    sys.stdout.flush()

    # ── 2. Upload do código ─────────────────────────────────────
    print("\n[2] Transferindo arquivos de código...")
    sys.stdout.flush()
    local_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # rankPulse root

    # Criar estrutura de diretórios no servidor
    dirs = [
        "", "config", "apps", "scripts",
        "apps/core", "apps/core/models",
        "apps/analytics", "apps/seo",
        "apps/content", "apps/checklists", "apps/channels",
        "apps/chat_support", "apps/payments",
        "templates", "templates/core", "templates/channels", "templates/components",
        "templates/pages", "templates/partials",
        "static", "static/css", "static/js", "static/img", "static/images", "logs", "credentials",
        "apps/core/templatetags",
        "apps/core/management", "apps/core/management/commands",
        "apps/analytics/management", "apps/analytics/management/commands",
        "apps/seo/management", "apps/seo/management/commands",
        "apps/content/management", "apps/content/management/commands",
        "apps/channels/management", "apps/channels/management/commands",
        "apps/core/migrations", "apps/analytics/migrations",
        "apps/seo/migrations", "apps/content/migrations",
        "apps/checklists/migrations", "apps/channels/migrations",
        "apps/chat_support/migrations", "apps/payments/migrations",
    ]
    for d in dirs:
        run_cmd(client, f"mkdir -p {BASE}/{d}")

    # Upload all Python files recursively
    files_uploaded = upload_dir(sftp, local_dir, BASE)
    print(f"    {len(files_uploaded)} arquivos transferidos")
    sys.stdout.flush()

    # ── 3. Transferir .env ──────────────────────────────────────
    print("\n[3] Transferindo .env...")
    sys.stdout.flush()
    env_local = os.path.join(local_dir, ".env")
    if os.path.exists(env_local):
        try:
            sftp.put(env_local, f"{BASE}/.env")
            print("    OK: .env")
        except Exception as e:
            print(f"    ERRO .env: {e}")
    else:
        print("    .env local não encontrado (usar .env do servidor)")
    sys.stdout.flush()

    sftp.close()

    # ── 4. Parar Gunicorn ───────────────────────────────────────
    print("\n[4] Parando Gunicorn (RankPulse)...")
    sys.stdout.flush()
    # Stop any systemd gunicorn that may occupy the same port
    run_cmd(client, "systemctl stop gunicorn-aresdev.service 2>/dev/null || true", timeout=10)
    run_cmd(client, f"pkill -f 'gunicorn.*config.wsgi.*{GUNICORN_PORT}'", timeout=10)
    time.sleep(2)
    print("    OK")
    sys.stdout.flush()

    # ── 5. Instalar dependências + migrations ───────────────────
    print("\n[5] Instalando dependências e aplicando migrations...")
    sys.stdout.flush()

    cmd = f"cd {BASE} && source venv/bin/activate && pip install -r requirements.txt 2>&1 | tail -3"
    out, err = run_cmd(client, cmd, timeout=180)
    print(f"    pip: {out.strip() if out else 'OK'}")
    sys.stdout.flush()

    # Reset DB se solicitado (--reset-db): apaga migrations antigas e recria o banco
    if RESET_DB:
        print("    ⚠️  RESET DB solicitado — apagando migrations e recriando banco...")
        sys.stdout.flush()
        # Apagar migration files (preserva __init__.py)
        for app in ("core", "channels", "analytics", "seo", "content", "checklists", "chat_support"):
            run_cmd(client, f"find {BASE}/apps/{app}/migrations -name '*.py' ! -name '__init__.py' -delete 2>/dev/null")
            run_cmd(client, f"find {BASE}/apps/{app}/migrations -name '*.pyc' -delete 2>/dev/null")
        # Detectar engine e resetar adequadamente
        db_engine_out, _ = run_cmd(client, f"grep -oP '(?<=DB_ENGINE=).*' {BASE}/.env 2>/dev/null")
        db_engine = db_engine_out.strip()
        if "postgresql" in db_engine:
            db_name_out, _ = run_cmd(client, f"grep -oP '(?<=DB_NAME=).*' {BASE}/.env 2>/dev/null")
            db_name = db_name_out.strip() or "rankpulse"
            run_cmd(client, f"sudo -u postgres psql -c 'DROP DATABASE IF EXISTS {db_name};' 2>&1", timeout=30)
            run_cmd(client, f"sudo -u postgres psql -c \"CREATE DATABASE {db_name} OWNER rankpulse;\" 2>&1", timeout=30)
            print(f"    DB PostgreSQL '{db_name}' recriado")
        else:
            run_cmd(client, f"rm -f {BASE}/db.sqlite3")
            print("    DB SQLite removido (será recriado pelo migrate)")
        sys.stdout.flush()

    # Gerar migrations para todos os apps (necessário pois migrations são criadas no servidor)
    cmd = f"cd {BASE} && source venv/bin/activate && python manage.py makemigrations core channels analytics seo content checklists chat_support payments 2>&1 | tail -10"
    out, err = run_cmd(client, cmd, timeout=60)
    print(f"    makemigrations: {out.strip() if out else 'OK'}")
    sys.stdout.flush()

    cmd = f"cd {BASE} && source venv/bin/activate && python manage.py migrate --noinput 2>&1 | tail -10"
    out, err = run_cmd(client, cmd, timeout=60)
    print(f"    migrate: {out.strip() if out else 'OK'}")
    sys.stdout.flush()

    # ── 6. Collectstatic ────────────────────────────────────────
    print("\n[6] Coletando arquivos estáticos...")
    sys.stdout.flush()
    cmd = f"cd {BASE} && source venv/bin/activate && python manage.py collectstatic --noinput 2>&1 | tail -1"
    out, err = run_cmd(client, cmd, timeout=60)
    print(f"    {out.strip() if out else 'OK'}")
    sys.stdout.flush()

    # ── 7. Iniciar Gunicorn ─────────────────────────────────────
    print("\n[7] Iniciando Gunicorn...")
    sys.stdout.flush()
    cmd = (
        f"cd {BASE} && source venv/bin/activate && "
        f"gunicorn config.wsgi:application "
        f"--bind=127.0.0.1:{GUNICORN_PORT} "
        f"--workers=2 --timeout=120 --daemon "
        f"--access-logfile={BASE}/logs/access.log "
        f"--error-logfile={BASE}/logs/error.log"
    )
    run_cmd(client, cmd, timeout=15)
    time.sleep(3)
    print("    Comando executado")
    sys.stdout.flush()

    # ── 8. Verificação ──────────────────────────────────────────
    print("\n[8] Verificando...")
    sys.stdout.flush()

    out, _ = run_cmd(client, f"ps aux | grep 'gunicorn.*{GUNICORN_PORT}' | grep -v grep | wc -l")
    procs = out.strip()
    print(f"    Processos Gunicorn: {procs}")

    out, _ = run_cmd(client, f"netstat -tlnp | grep {GUNICORN_PORT}")
    if GUNICORN_PORT in out:
        print(f"    Porta {GUNICORN_PORT}: OK")
    else:
        print(f"    Porta {GUNICORN_PORT}: NAO ATIVA")
        out, _ = run_cmd(client, f"tail -10 {BASE}/logs/error.log 2>/dev/null || echo 'sem log'")
        print(f"    Log: {out[:300]}")
    sys.stdout.flush()

    # ── 9. Teste HTTP local ─────────────────────────────────────
    print("\n[9] Teste HTTP local...")
    sys.stdout.flush()
    out, _ = run_cmd(client, f"curl -s -w '|%{{http_code}}' -o /dev/null http://127.0.0.1:{GUNICORN_PORT}/")
    print(f"    Resposta: {out}")
    sys.stdout.flush()

    client.close()

    # ── 10. Teste externo ───────────────────────────────────────
    print(f"\n[10] Teste externo (https://{DOMAIN}/)...")
    sys.stdout.flush()
    try:
        import requests
        r = requests.get(f"https://{DOMAIN}/", verify=False, timeout=10)
        print(f"    Status: {r.status_code}")
        if r.status_code == 200:
            print("    SITE FUNCIONANDO!")
        else:
            print(f"    Conteudo: {r.text[:150]}")
    except Exception as e:
        print(f"    Erro: {e}")
        print("    (Normal se DNS ainda não propagou ou SSL não configurado)")

    print("\n" + "=" * 60)
    print("DEPLOY CONCLUIDO")
    print("=" * 60)
    sys.stdout.flush()

    # ── 11. Push para GitHub ────────────────────────────────────
    print("\n[11] Atualizando GitHub...")
    sys.stdout.flush()
    try:
        git_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # rankPulse root

        result = subprocess.run(["git", "add", "-A"], capture_output=True, text=True, cwd=git_dir)
        commit_msg = f"Deploy {timestamp}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True, text=True, cwd=git_dir,
        )

        if "nothing to commit" in (result.stdout + result.stderr):
            print("    Nada para commitar")
        else:
            result = subprocess.run(
                ["git", "push", "origin", "main"],
                capture_output=True, text=True, cwd=git_dir,
            )
            if result.returncode == 0:
                print(f"    Commit: {commit_msg}")
                print("    Push para GitHub: OK")
            else:
                result = subprocess.run(
                    ["git", "push", "origin", "master"],
                    capture_output=True, text=True, cwd=git_dir,
                )
                if result.returncode == 0:
                    print(f"    Commit: {commit_msg}")
                    print("    Push para GitHub: OK")
                else:
                    print(f"    Push falhou: {result.stderr[:100]}")
    except Exception as e:
        print(f"    GitHub: {e}")
    sys.stdout.flush()

    print("\n" + "=" * 60)
    print("PROCESSO FINALIZADO")
    print("=" * 60)
    print(f"\nBackups no servidor:")
    print(f"  DB:     {BASE}/backups/db/")
    print(f"  Código: {BASE}/backups/code/")


if __name__ == "__main__":
    main()
