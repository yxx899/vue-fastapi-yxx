#!/usr/bin/env python3
"""Install local deploy public key into remote authorized_keys (one-time)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

HOST = os.environ.get("DEPLOY_HOST", "47.95.28.202")
USER = os.environ.get("DEPLOY_USER", "root")
PASSWORD = os.environ.get("DEPLOY_PASSWORD", "")
PUB_PATH = Path(os.environ.get("DEPLOY_PUBKEY", Path.home() / ".ssh" / "kb_deploy_ed25519.pub"))


def main() -> int:
    if not PASSWORD:
        print("DEPLOY_PASSWORD required", file=sys.stderr)
        return 1
    if not PUB_PATH.exists():
        print(f"missing pubkey: {PUB_PATH}", file=sys.stderr)
        return 1
    pub = PUB_PATH.read_text(encoding="utf-8").strip()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
    cmd = f"""
set -e
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
grep -qxF '{pub}' ~/.ssh/authorized_keys || echo '{pub}' >> ~/.ssh/authorized_keys
echo OK
wc -l ~/.ssh/authorized_keys
"""
    _, stdout, stderr = ssh.exec_command(cmd, timeout=60, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    # also ensure base packages for future deploy
    _, stdout, _ = ssh.exec_command(
        "export DEBIAN_FRONTEND=noninteractive; "
        "apt-get update -y >/dev/null && apt-get install -y rsync curl nginx python3-venv >/dev/null; "
        "mkdir -p /opt/kb/backend/data /opt/kb/frontend /opt/kb/scripts; "
        "echo packages_ok",
        timeout=300,
        get_pty=True,
    )
    print(stdout.read().decode("utf-8", errors="replace"))
    ssh.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
