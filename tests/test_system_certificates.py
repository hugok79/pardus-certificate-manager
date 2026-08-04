"""
Unit tests for system certificate helpers, store loading, and the admin helper.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

# so we can import the app modules the same way the app does
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from system.certificate_info import (
    cert_info,
    fingerprint_sha256,
    is_ca,
    is_duplicate,
    is_self_signed,
    validity_status,
)
import system.system_cert_admin as admin
from system.system_cert_store import _display_name, load_certificate


def make_cert(common_name="Test CA", is_ca_flag=True, days_before=-1, days_after=30):
    """Small throwaway certificate for tests."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(timezone.utc)
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now + timedelta(days=days_before))
        .not_valid_after(now + timedelta(days=days_after))
        .add_extension(x509.BasicConstraints(ca=is_ca_flag, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )


def test_fingerprint_looks_like_sha256():
    cert = make_cert()
    fp = fingerprint_sha256(cert)
    assert len(fp) == 64
    assert fp == fingerprint_sha256(cert)


def test_ca_and_self_signed_flags():
    ca = make_cert(is_ca_flag=True)
    leaf = make_cert(common_name="Leaf", is_ca_flag=False)

    assert is_ca(ca) is True
    assert is_ca(leaf) is False
    assert is_self_signed(ca) is True


def test_validity_status():
    assert validity_status(make_cert()) == "valid"
    assert validity_status(make_cert(days_before=-60, days_after=-1)) == "expired"
    assert validity_status(make_cert(days_before=1, days_after=60)) == "not_yet_valid"


def test_duplicate_detection():
    a = make_cert(common_name="A")
    b = make_cert(common_name="B")
    assert is_duplicate(a, [a, b]) is True
    assert is_duplicate(a, [b]) is False


def test_cert_info_preview_fields():
    cert = make_cert(common_name="Pardus Test CA")
    info = cert_info(cert)

    assert "Pardus Test CA" in info["subject"]
    assert info["fingerprint"] == fingerprint_sha256(cert)
    assert info["status"] == "valid"
    assert info["is_ca"] is True


def test_load_certificate_from_pem(tmp_path):
    cert = make_cert(common_name="From File")
    path = tmp_path / "ca.crt"
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    loaded = load_certificate(path)
    assert loaded is not None
    assert _display_name(loaded, "fallback") == "From File"
    assert load_certificate(tmp_path / "missing.crt") is None


def test_admin_destination_name_rules(tmp_path, monkeypatch):
    monkeypatch.setattr(admin, "LOCAL_CA_DIR", tmp_path)

    assert admin._destination("my-ca.crt") == tmp_path / "my-ca.crt"
    # path tricks should collapse to basename only
    assert admin._destination("../../evil.crt") == tmp_path / "evil.crt"

    with pytest.raises(SystemExit):
        admin._destination("not-a-crt")


def test_admin_install_and_remove(tmp_path, monkeypatch):
    monkeypatch.setattr(admin, "LOCAL_CA_DIR", tmp_path)
    source = tmp_path / "incoming.pem"
    source.write_bytes(make_cert().public_bytes(serialization.Encoding.PEM))

    with patch("system.system_cert_admin.subprocess.run"):
        admin.main(["system_cert_admin.py", "install", str(source), "test-ca.crt"])
    assert (tmp_path / "test-ca.crt").is_file()

    with patch("system.system_cert_admin.subprocess.run"):
        admin.main(["system_cert_admin.py", "remove", "test-ca.crt"])
    assert not (tmp_path / "test-ca.crt").exists()
