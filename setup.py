#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os, subprocess


def create_mo_files():
    podir = "po"
    mo = []
    for po in os.listdir(podir):
        if po.endswith(".po"):
            os.makedirs(
                "{}/{}/LC_MESSAGES".format(podir, po.split(".po")[0]), exist_ok=True
            )
            mo_file = "{}/{}/LC_MESSAGES/{}".format(
                podir, po.split(".po")[0], "pardus-certificate-manager.mo"
            )
            msgfmt_cmd = "msgfmt {} -o {}".format(podir + "/" + po, mo_file)
            subprocess.call(msgfmt_cmd, shell=True)
            mo.append(
                (
                    "/usr/share/locale/" + po.split(".po")[0] + "/LC_MESSAGES",
                    ["po/" + po.split(".po")[0] + "/LC_MESSAGES/pardus-certificate-manager.mo"],
                )
            )
    return mo


version = "0.0.0"
changelog = "debian/changelog"
if os.path.exists(changelog):
    head = open(changelog).readline()
    try:
        version = head.split("(")[1].split(")")[0]
    except:
        print("debian/changelog format is wrong for get version")
        version = "0.0.0"
    f = open("src/__version__", "w")
    f.write(version)
    f.close()

data_files = [
    ("/usr/bin", ["pardus-certificate-manager"]),
    ("/usr/share/applications", ["data/tr.org.pardus.certificate-manager.desktop"]),
    ("/usr/share/pardus/pardus-certificate-manager/ui", ["ui/MainWindow.glade"]),
    (
        "/usr/share/pardus/pardus-certificate-manager/src",
        [
            "src/Main.py",
            "src/MainWindow.py",
            "src/__version__",
        ],
    ),
    (
        "/usr/share/pardus/pardus-certificate-manager/src/browsers",
        [
            "src/browsers/__init__.py",
            "src/browsers/browser_cert_store.py",
        ],
    ),
    (
        "/usr/share/pardus/pardus-certificate-manager/src/system",
        [
            "src/system/__init__.py",
            "src/system/certificate_info.py",
            "src/system/system_cert_store.py",
        ],
    ),
    (
        "/usr/libexec/pardus-certificate-manager",
        ["src/system/system_cert_admin.py"],
    ),
    (
        "/usr/share/pardus/pardus-certificate-manager/data",
        ["data/pardus-certificate-manager.svg"]
    ),
    (
        "/usr/share/polkit-1/actions",
        ["data/tr.org.pardus.pkexec.pardus-certificate-manager.policy"]
    ),
    (
        "/usr/share/icons/hicolor/scalable/apps/",
        ["data/pardus-certificate-manager.svg"]
    )
] + create_mo_files()


setup(
    name="pardus-certificate-manager",
    version=version,
    packages=find_packages(),
    scripts=["pardus-certificate-manager"],
    install_requires=["PyGObject", "cryptography"],
    data_files=data_files,
    author="Emel Öztürk",
    author_email="emel.ozturk@pardus.org.tr",
    description="Certificate manager application for Pardus",
    license="GPLv3",
    keywords="pardus-certificate-manager, certificate-manager",
    url="https://github.com/pardus/pardus-certificate-manager",
)
