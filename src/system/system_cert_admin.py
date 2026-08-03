#!/usr/bin/python3
"""
Privileged helper for the system trust store.

Runs as root via pkexec
It copies one CA certificate into /usr/local/share/ca-certificates (or removes)
refreshes the trust store.

    system_cert_admin.py install <source.pem> <name.crt>
    system_cert_admin.py remove  <name.crt>
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

LOCAL_CA_DIR = Path("/usr/local/share/ca-certificates")
_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.crt$")


def _destination(name):
    safe = Path(name).name
    if not _NAME_RE.fullmatch(safe):
        sys.exit(f"invalid certificate name: {name}")
    return LOCAL_CA_DIR / safe


def main(argv):
    # system_cert_admin.py - install - source.pem - destination.crt
    if len(argv) == 4 and argv[1] == "install":
        LOCAL_CA_DIR.mkdir(parents=True, exist_ok=True)
        dest = _destination(argv[3])
        if dest.exists():
            sys.exit(f"certificate already exists: {dest.name}")
        shutil.copyfile(argv[2], dest)
        os.chmod(dest, 0o644)
        subprocess.run(["update-ca-certificates"], check=True)
    # system_cert_admin.py - remove - destination.crt
    elif len(argv) == 3 and argv[1] == "remove":
        _destination(argv[2]).unlink(missing_ok=True)
        subprocess.run(["update-ca-certificates", "--fresh"], check=True)
    else:
        sys.exit("usage: system_cert_admin.py install <source> <name> | remove <name>")


if __name__ == "__main__":
    main(sys.argv)
