from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID

SYSTEM_CERT_DIR = Path("/etc/ssl/certs")


@dataclass(frozen=True)
class CertificateItem:
    name: str
    path: Path
    source: str  # system-user-imported


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


def list_system_certificates():
    if not SYSTEM_CERT_DIR.exists():
        return []

    items = []
    for path in sorted(SYSTEM_CERT_DIR.glob("*.pem")):
        cert = load_certificate(path)
        if cert is None:
            continue
        name = _display_name(cert, path.stem)
        items.append(CertificateItem(name, path, "system"))
    return items


def list_all_certificates():
    return list_system_certificates()
