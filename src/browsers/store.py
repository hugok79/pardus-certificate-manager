"""
Browser certificate store access (Firefox & Chrome/Chromium)

Both browsers use NSS dbs on Linux, underlyingoperations
(list/import/export/delete via certutil) are identical.
Only the db *location* differs:

  - Firefox: one cert9.db per profile, discovered via profiles.ini
  - Chrome/Chromium: one shared cert db at ~/.pki/nssdb, no profiles
"""

import configparser
import subprocess
from dataclasses import dataclass
from pathlib import Path

FIREFOX_CONFIG_DIR = Path.home() / ".mozilla" / "firefox"
CHROME_NSSDB_PATH = Path.home() / ".pki" / "nssdb"


@dataclass(frozen=True)
class BrowserProfile:
    browser: str
    label: str
    db_path: Path


@dataclass(frozen=True)
class BrowserCertificate:
    nickname: str
    profile: BrowserProfile


def list_firefox_profiles():
    ini_path = FIREFOX_CONFIG_DIR / "profiles.ini"
    if not ini_path.exists():
        return []

    config = configparser.ConfigParser()
    config.read(ini_path)

    profiles = []
    for section in config.sections():
        if not section.startswith("Profile"):
            continue
        path = config[section].get("Path")
        if not path:
            continue
        name = config[section].get("Name", path)
        is_relative = config[section].get("IsRelative", "1") == "1"
        db_path = (FIREFOX_CONFIG_DIR / path) if is_relative else Path(path)
        if db_path.exists():
            profiles.append(BrowserProfile("firefox", f"Firefox — {name}", db_path))
    return profiles


def list_chrome_profiles():
    if not CHROME_NSSDB_PATH.exists():
        return []
    return [BrowserProfile("chrome", "Chrome", CHROME_NSSDB_PATH)]


def list_profiles():
    return list_firefox_profiles() + list_chrome_profiles()


def _run_certutil(args):
    try:
        return subprocess.run(
            ["certutil", *args],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return None


def list_certificates(profile):
    """
    List certificate nicknames from profile db
    """
    result = _run_certutil(["-L", "-d", f"sql:{profile.db_path}"])
    if result.returncode != 0:
        return []

    certs = []
    for line in result.stdout.splitlines():
        line = line.rstrip()
        if not line or line.startswith("Certificate Nickname") or set[str](line) == {"-"}:
            continue
        nickname = line.rsplit(None, 1)[0].strip()
        if nickname:
            certs.append(BrowserCertificate(nickname, profile))
    return certs


def export_certificate_pem(profile, nickname):
    """
    Return PEM text for a certificate by nickname
    """
    result = _run_certutil(
        ["-L", "-n", nickname, "-a", "-d", f"sql:{profile.db_path}"]
    )
    if result.returncode != 0:
        return None
    print(result.stdout)
    return result.stdout


def install_certificate(profile, pem_path, nickname, trust="C,,"):
    """
    Install a certificate into profile db
    """
    result = _run_certutil(
        ["-A", "-n", nickname, "-t", trust, "-i",
         str(pem_path), "-d", f"sql:{profile.db_path}"],
    )
    return result.returncode == 0


def delete_certificate(profile, nickname):
    result = _run_certutil(
        ["-D", "-n", nickname, "-d", f"sql:{profile.db_path}"]
    )
    return result.returncode == 0
