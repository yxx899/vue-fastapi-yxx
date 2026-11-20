#!/usr/bin/env python3
"""Local dry-run of the CI deploy path using the deploy SSH key (no password).

Builds frontend locally, syncs backend + frontend/dist + scripts, then runs remote_deploy.sh.
Does not overwrite remote backend/data or backend/.env.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import paramiko

HOST = os.environ.get("DEPLOY_HOST", "47.95.28.202")
USER = os.environ.get("DEPLOY_USER", "root")
PATH_REMOTE = os.environ.get("DEPLOY_PATH", "/opt/kb")
KEY = Path(os.environ.get("DEPLOY_SSH_KEY_FILE", Path.home() / ".ssh" / "kb_deploy_ed25519"))
ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".venv", "data", "node_modules", "__pycache__", ".git"}
EXCLUDE_FILES = {".env", ".env.local"}


def run(cmd: list[str], **kwargs) -> None:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.check_call(cmd, **kwargs)


def build_frontend() -> None:
    frontend = ROOT / "frontend"
    run(["npm", "ci"], cwd=frontend, shell=True)
    run(["npm", "run", "build"], cwd=frontend, shell=True)
    if not (frontend / "dist" / "index.html").exists():
        raise SystemExit("frontend build failed: dist/index.html missing")


def add_tree(tar: tarfile.TarFile, rel: str) -> None:
    base = ROOT / rel
    if base.is_file():
        tar.add(base, arcname=rel.replace("\\", "/"))
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            if name in EXCLUDE_FILES or name.endswith(".pyc"):
                continue
            p = Path(dirpath) / name
            arc = p.relative_to(ROOT).as_posix()
            if set(Path(arc).parts) & EXCLUDE_DIRS:
                continue
            tar.add(p, arcname=arc)


def make_archive() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        add_tree(tar, "backend")
        add_tree(tar, "frontend/dist")
        add_tree(tar, "scripts")
        for f in ("docker-compose.yml", "README.md"):
            if (ROOT / f).exists():
                add_tree(tar, f)
    return buf.getvalue()


def main() -> int:
    if not KEY.exists():
        print(f"missing key {KEY}", file=sys.stderr)
        return 1

    print("==> build frontend", flush=True)
    build_frontend()
    print("==> pack", flush=True)
    archive = make_archive()
    print(f"==> archive {len(archive)/1024/1024:.2f} MB", flush=True)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST,
        username=USER,
        key_filename=str(KEY),
        timeout=30,
        allow_agent=False,
        look_for_keys=False,
    )
    sftp = client.open_sftp()
    with sftp.file("/tmp/kb-ci.tar.gz", "wb") as f:
        f.write(archive)
    sftp.close()

    cmd = f"""
set -euo pipefail
rm -rf /tmp/kb-ci-extract
mkdir -p /tmp/kb-ci-extract
tar -xzf /tmp/kb-ci.tar.gz -C /tmp/kb-ci-extract
# preserve data and .env
if [ -d {PATH_REMOTE}/backend/data ]; then
  cp -a {PATH_REMOTE}/backend/data /tmp/kb-data-preserve
fi
if [ -f {PATH_REMOTE}/backend/.env ]; then
  cp -a {PATH_REMOTE}/backend/.env /tmp/kb-env-preserve
fi
mkdir -p {PATH_REMOTE}
# sync trees without wiping venv mid-flight awkwardly: replace code dirs then restore data/env
rm -rf {PATH_REMOTE}/backend/app {PATH_REMOTE}/backend/scripts {PATH_REMOTE}/backend/docs
cp -a /tmp/kb-ci-extract/backend/. {PATH_REMOTE}/backend/
cp -a /tmp/kb-ci-extract/frontend {PATH_REMOTE}/
cp -a /tmp/kb-ci-extract/scripts {PATH_REMOTE}/
cp -a /tmp/kb-ci-extract/docker-compose.yml {PATH_REMOTE}/ 2>/dev/null || true
cp -a /tmp/kb-ci-extract/README.md {PATH_REMOTE}/ 2>/dev/null || true
if [ -d /tmp/kb-data-preserve ]; then
  rm -rf {PATH_REMOTE}/backend/data
  mv /tmp/kb-data-preserve {PATH_REMOTE}/backend/data
fi
if [ -f /tmp/kb-env-preserve ]; then
  cp -a /tmp/kb-env-preserve {PATH_REMOTE}/backend/.env
fi
# strip CRLF if any
sed -i 's/\\r$//' {PATH_REMOTE}/scripts/remote_deploy.sh
chmod +x {PATH_REMOTE}/scripts/remote_deploy.sh
export DEPLOY_PATH={PATH_REMOTE}
bash {PATH_REMOTE}/scripts/remote_deploy.sh
"""
    print("==> remote deploy", flush=True)
    _, stdout, stderr = client.exec_command(cmd, timeout=900, get_pty=True)
    # stream output
    while True:
        line = stdout.readline()
        if not line:
            break
        try:
            print(line, end="", flush=True)
        except UnicodeEncodeError:
            sys.stdout.buffer.write(line.encode("utf-8", errors="replace") if isinstance(line, str) else line)
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print(err, file=sys.stderr)
    code = stdout.channel.recv_exit_status()
    client.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
