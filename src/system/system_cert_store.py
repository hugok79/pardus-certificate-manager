import subprocess
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID

from system.certificate_info import fingerprint_sha256

SYSTEM_CERT_DIR = Path("/etc/ssl/certs")
LOCAL_CA_DIR = Path("/usr/local/share/ca-certificates")
_HELPER = Path("/usr/libexec/pardus-certificate-manager/system_cert_admin.py")


@dataclass(frozen=True)
class CertificateItem:
    name: str
    path: Path
    source: str  # system-user-imported
    removable_name: str = None

def load_certificate(path):
    try:
        return x509.load_pem_x509_certificate(path.read_bytes())
    except (OSError, ValueError):
        return None


def _display_name(cert, fallback):
    for oid in (NameOID.COMMON_NAME, NameOID.ORGANIZATION_NAME):
        attrs = cert.subject.get_attributes_for_oid(oid)
        if attrs:
            return attrs[0].value
    return fallback


def list_user_certificates():
    if not LOCAL_CA_DIR.exists():
        return []

    items = []
    for path in sorted(LOCAL_CA_DIR.glob("*.crt")):
        cert = load_certificate(path)
        if cert is None:
            continue
        name = _display_name(cert, path.stem)
        items.append(CertificateItem(name, path, "user", path.name))
    return items


def list_system_certificates(skip_fingerprints=frozenset()):
    if not SYSTEM_CERT_DIR.exists():
        return []

    items = []
    for path in sorted(SYSTEM_CERT_DIR.glob("*.pem")):
        cert = load_certificate(path)
        if cert is None:
            continue
        if fingerprint_sha256(cert) in skip_fingerprints:
            continue
        name = _display_name(cert, path.stem)
        items.append(CertificateItem(name, path, "system"))
    return items


def list_all_certificates():
    user = list_user_certificates()
    # User added certs symlinked into /etc/ssl/certs, show it only once
    seen = {
        fingerprint_sha256(cert)
        for item in user
        if (cert := load_certificate(item.path)) is not None
    }
    return user + list_system_certificates(seen)


def install_certificate(source_path):
    """
    Install a PEM cert into the system trust store
    """
    source = Path(source_path)
    cert = load_certificate(source)
    if cert is None:
        return False
    name = fingerprint_sha256(cert) + ".crt"
    result = subprocess.run(
        ["pkexec", str(_HELPER), "install", str(source), name],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0


def remove_certificate(removable_name):
    """
    Remove a user added cert from the system trust store
    """
    result = subprocess.run(
        ["pkexec", str(_HELPER), "remove", removable_name],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0

