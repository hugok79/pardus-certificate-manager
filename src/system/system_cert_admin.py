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
import shutil
import subprocess
import sys
from pathlib import Path

LOCAL_CA_DIR = Path("/usr/local/share/ca-certificates")


def _destination(name):
    safe = Path(name).name
    if not safe.endswith(".crt"):
        sys.exit(f"invalid certificate name: {name}")
    return LOCAL_CA_DIR / safe


def main(argv):
    # system_cert_admin.py - install - source.pem - destination.crt
    if len(argv) == 4 and argv[1] == "install":
        LOCAL_CA_DIR.mkdir(parents=True, exist_ok=True)
        dest = _destination(argv[3])
        shutil.copy(argv[2], dest)
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
