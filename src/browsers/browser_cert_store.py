"""
Browser certificate store access (Firefox & Chrome/Chromium)

Both browsers use NSS dbs on Linux, underlying operations
(list/import/export/delete via certutil) are identical.
Only the db *location* differs:

  - Firefox: one cert9.db per profile, discovered via profiles.ini
  - Chrome/Chromium: one shared cert db at ~/.pki/nssdb, no profiles

A browser is only listed when it is installed.
"""

import configparser
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

FIREFOX_CONFIG_DIR = Path.home() / ".mozilla" / "firefox"
FIREFOX_COMMANDS = ("firefox", "firefox-esr")

CHROME_NSSDB_PATH = Path.home() / ".pki" / "nssdb"
CHROME_COMMANDS = (
    ("google-chrome", "Chrome"),
    ("google-chrome-stable", "Chrome"),
    ("chromium", "Chromium"),
    ("chromium-browser", "Chromium"),
)


@dataclass(frozen=True)
class BrowserProfile:
    browser: str
    label: str
    db_path: Path


@dataclass(frozen=True)
class BrowserCertificate:
    nickname: str
    profile: BrowserProfile


def _command_exists(command):
    return shutil.which(command) is not None


def _is_nss_db(path):
    """
    A directory is a usable NSS db only if it holds cert9.db
    """
    return (path / "cert9.db").is_file()


def _firefox_installed():
    return any(_command_exists(cmd) for cmd in FIREFOX_COMMANDS)


def _chrome_label():
    """
    Return label if chrome/chromium is installed
    """
    for command, label in CHROME_COMMANDS:
        if _command_exists(command):
            return label
    return None


def list_firefox_profiles():
    if not _firefox_installed():
        return []

    ini_path = FIREFOX_CONFIG_DIR / "profiles.ini"
    if not ini_path.is_file():
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
        if _is_nss_db(db_path):
            profiles.append(BrowserProfile("firefox", f"Firefox — {name}", db_path))
    return profiles


def list_chrome_profiles():
    label = _chrome_label()
    if label is None or not _is_nss_db(CHROME_NSSDB_PATH):
        return []
    return [BrowserProfile("chrome", label, CHROME_NSSDB_PATH)]


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


def _ran_successfully(result):
    return result is not None and result.returncode == 0


def list_certificates(profile):
    """
    List certificate nicknames from profile db
    """
    result = _run_certutil(["-L", "-d", f"sql:{profile.db_path}"])
    if not _ran_successfully(result):
        return []

    certs = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        # Header ("Certificate Nickname...", "SSL,S/MIME,JAR/XPI") and
        # separator ("-----") lines are not certificates, skip
        if (
            not stripped
            or stripped.startswith("Certificate Nickname")
            or stripped.startswith("SSL,")
            or set(stripped) == {"-"}
        ):
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
    if not _ran_successfully(result):
        return None
    return result.stdout


def install_certificate(profile, pem_path, nickname, trust="C,,"):
    """
    Install a certificate into profile db
    """
    result = _run_certutil(
        ["-A", "-n", nickname, "-t", trust, "-i",
         str(pem_path), "-d", f"sql:{profile.db_path}"],
    )
    return _ran_successfully(result)


def delete_certificate(profile, nickname):
    result = _run_certutil(
        ["-D", "-n", nickname, "-d", f"sql:{profile.db_path}"]
    )
    return _ran_successfully(result)
