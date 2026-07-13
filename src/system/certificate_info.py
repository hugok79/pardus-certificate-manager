from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes


def fingerprint_sha256(cert):
    """
    Generate fingerprint for the certificate
    """
    return cert.fingerprint(hashes.SHA256()).hex()


def is_ca(cert):
    """
    Check if the certificate is a CA certificate
    Return True if cert has basic constraints extension
    """
    try:
        constraints = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        is_ca_cert = bool(constraints.value.ca)
        return is_ca_cert
    except x509.ExtensionNotFound:
        return False


def is_self_signed(cert):
    """
    Return True if cert is self signed
    """
    return cert.subject == cert.issuer


def _valid_period(cert):
    """
    Return valid period for the cert
    Works on both deb 12 & 13
    """
    if hasattr(cert, "not_valid_before_utc"):
        return cert.not_valid_before_utc, cert.not_valid_after_utc
    not_before = cert.not_valid_before.replace(tzinfo=timezone.utc)
    not_after = cert.not_valid_after.replace(tzinfo=timezone.utc)
    return not_before, not_after


def validity_status(cert):
    """
    Return validity status depending on the current time
    """
    not_before, not_after = _valid_period(cert)
    now = datetime.now(timezone.utc)
    if now < not_before:
        return "not_yet_valid"
    if now > not_after:
        return "expired"
    return "valid"


def is_duplicate(cert, existing_certs):
    """
    Returns True if cert's fingerprint matches any existing one
    """
    fp = fingerprint_sha256(cert)
    for other in existing_certs:
        if fingerprint_sha256(other) == fp:
            return True
    return False


def cert_info(cert):
    """
    Return fields as a dict, use to show for preview
    """
    not_before, not_after = _valid_period(cert)
    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "not_before": not_before.strftime("%Y-%m-%d"),
        "not_after": not_after.strftime("%Y-%m-%d"),
        "fingerprint": fingerprint_sha256(cert),
        "serial": format(cert.serial_number, "x"),
        "is_ca": is_ca(cert),
        "is_self_signed": is_self_signed(cert),
        "status": validity_status(cert),
    }
