"""
Unit tests for browser NSS profile discovery and certutil-backed ops.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from browsers import browser_cert_store as browsers
from browsers.browser_cert_store import BrowserCertificate, BrowserProfile


def test_nss_db_needs_cert9(tmp_path):
    assert browsers._is_nss_db(tmp_path) is False
    (tmp_path / "cert9.db").write_bytes(b"fake")
    assert browsers._is_nss_db(tmp_path) is True


def test_list_firefox_profiles_from_ini(tmp_path, monkeypatch):
    profile_dir = tmp_path / "abcd.default"
    profile_dir.mkdir()
    (profile_dir / "cert9.db").write_bytes(b"fake")

    (tmp_path / "profiles.ini").write_text(
        "[Profile0]\n"
        "Name=default\n"
        "IsRelative=1\n"
        "Path=abcd.default\n"
    )
    monkeypatch.setattr(browsers, "FIREFOX_CONFIG_DIR", tmp_path)

    with patch.object(browsers, "_firefox_installed", return_value=True):
        profiles = browsers.list_firefox_profiles()

    assert len(profiles) == 1
    assert profiles[0].browser == "firefox"
    assert "default" in profiles[0].label
    assert profiles[0].db_path == profile_dir


def test_list_firefox_skips_profile_without_db(tmp_path, monkeypatch):
    (tmp_path / "empty.default").mkdir()
    (tmp_path / "profiles.ini").write_text(
        "[Profile0]\n"
        "Name=empty\n"
        "IsRelative=1\n"
        "Path=empty.default\n"
    )
    monkeypatch.setattr(browsers, "FIREFOX_CONFIG_DIR", tmp_path)

    with patch.object(browsers, "_firefox_installed", return_value=True):
        assert browsers.list_firefox_profiles() == []


def test_list_chrome_profiles_when_db_exists(tmp_path, monkeypatch):
    (tmp_path / "cert9.db").write_bytes(b"fake")
    monkeypatch.setattr(browsers, "CHROME_NSSDB_PATH", tmp_path)

    with patch.object(browsers, "_chrome_label", return_value="Chromium"):
        profiles = browsers.list_chrome_profiles()

    assert len(profiles) == 1
    assert profiles[0].browser == "chrome"
    assert profiles[0].label == "Chromium"


def test_list_chrome_empty_without_db(tmp_path, monkeypatch):
    monkeypatch.setattr(browsers, "CHROME_NSSDB_PATH", tmp_path)
    with patch.object(browsers, "_chrome_label", return_value="Chrome"):
        assert browsers.list_chrome_profiles() == []


def test_list_certificates_parses_certutil_output():
    profile = BrowserProfile("firefox", "Firefox — default", Path("/tmp/db"))
    stdout = (
        "Certificate Nickname                                         Trust Attributes\n"
        "                                                             SSL,S/MIME,JAR/XPI\n"
        "\n"
        "Pardus Root CA                                               C,,\n"
        "----------------------\n"
        "My Site Cert                                                 u,u,u\n"
    )
    result = SimpleNamespace(returncode=0, stdout=stdout)

    with patch.object(browsers, "_run_certutil", return_value=result):
        certs = browsers.list_certificates(profile)

    assert [c.nickname for c in certs] == ["Pardus Root CA", "My Site Cert"]
    assert all(isinstance(c, BrowserCertificate) for c in certs)


def test_list_certificates_empty_when_certutil_fails():
    profile = BrowserProfile("firefox", "Firefox — default", Path("/tmp/db"))
    with patch.object(browsers, "_run_certutil", return_value=None):
        assert browsers.list_certificates(profile) == []


def test_install_uses_trusted_ca_flag(tmp_path):
    profile = BrowserProfile("chrome", "Chrome", tmp_path)
    pem = tmp_path / "ca.pem"
    pem.write_text("dummy")
    ok = SimpleNamespace(returncode=0, stdout="")

    with patch.object(browsers, "_run_certutil", return_value=ok) as run:
        assert browsers.install_certificate(profile, pem, "MyCA") is True

    args = run.call_args[0][0]
    assert args[:2] == ["-A", "-n"]
    assert "MyCA" in args
    assert "-t" in args
    assert args[args.index("-t") + 1] == "C,,"
    assert f"sql:{tmp_path}" in args


def test_export_and_delete(tmp_path):
    profile = BrowserProfile("chrome", "Chrome", tmp_path)
    pem_text = "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n"
    ok = SimpleNamespace(returncode=0, stdout=pem_text)

    with patch.object(browsers, "_run_certutil", return_value=ok) as run:
        assert browsers.export_certificate_pem(profile, "nick") == pem_text
        assert browsers.delete_certificate(profile, "nick") is True

    assert run.call_count == 2
