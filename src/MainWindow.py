import os
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import locale
from locale import gettext as _

from pathlib import Path

from system.certificate_store import list_all_certificates, load_certificate
from system.certificate_info import cert_info
from browsers import store as browser_store

# Development: ../locale, Production: /usr/share/locale
localedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../locale")
if not os.path.exists(localedir):
    localedir = "/usr/share/locale"

locale.bindtextdomain("pardus-certificate-manager", localedir)
locale.textdomain("pardus-certificate-manager")
_ = locale.gettext


class MainWindow:
    def __init__(self, application):
        self.builder = Gtk.Builder()

        # Import UI file
        glade_file = (
            os.path.dirname(os.path.abspath(__file__)) + "/../ui/MainWindow.glade"
        )
        self.builder.add_from_file(glade_file)
        self.builder.connect_signals(self)

        self.define_components()
        self.load_certificates()
        self.load_browser_profiles()

        self.window.set_application(application)
        self.window.show_all()

    def define_components(self):
        # Window
        self.window = self.builder.get_object("main_window")
        self.window.set_position(Gtk.WindowPosition.CENTER)

        # Header bar
        self.header_bar = self.builder.get_object("header_bar")

        # Buttons
        self.add_button = self.builder.get_object("add_button")
        self.delete_button = self.builder.get_object("delete_button")
        self.refresh_button = self.builder.get_object("refresh_button")
        self.menu_button = self.builder.get_object("menu_button")
        self.menu_about = self.builder.get_object("menu_about")
        self.menu_settings = self.builder.get_object("menu_settings")

        # Certificate list
        self.cert_listbox = self.builder.get_object("cert_listbox")

        # Popover
        self.menu_popover = self.builder.get_object("menu_popover")

        # About dialog
        self.about_dialog = self.builder.get_object("about_dialog")
        self.about_dialog.set_transient_for(self.window)

        # Import file chooser
        self.import_chooser = self.builder.get_object("import_chooser")
        self.import_chooser.set_transient_for(self.window)

        # Certificate details dialog
        self.cert_details_dialog = self.builder.get_object("cert_details_dialog")
        self.cert_details_dialog.set_transient_for(self.window)
        self.details_warning_label = self.builder.get_object("details_warning_label")
        self.details_values = {
            "file": self.builder.get_object("details_file_value"),
            "subject": self.builder.get_object("details_subject_value"),
            "issuer": self.builder.get_object("details_issuer_value"),
            "not_before": self.builder.get_object("details_valid_from_value"),
            "not_after": self.builder.get_object("details_valid_until_value"),
            "serial": self.builder.get_object("details_serial_value"),
            "fingerprint": self.builder.get_object("details_fingerprint_value"),
            "is_ca": self.builder.get_object("details_ca_value"),
            "status": self.builder.get_object("details_status_value"),
        }

        # System page signals
        self.add_button.connect("clicked", self.on_add_button_clicked)
        self.delete_button.connect("clicked", self.on_delete_button_clicked)
        self.refresh_button.connect("clicked", self.on_refresh_button_clicked)
        self.menu_about.connect("clicked", self.on_menu_about_clicked)
        self.menu_settings.connect("clicked", self.on_menu_settings_clicked)

        # Browser page elements & signals
        self.browser_combo = self.builder.get_object("browser_combo")
        self.browser_listbox = self.builder.get_object("browser_listbox")
        self.browser_import_button = self.builder.get_object("browser_import_button")
        self.browser_export_button = self.builder.get_object("browser_export_button")
        self.browser_delete_button = self.builder.get_object("browser_delete_button")
        self.browser_profiles = []
        self.selected_browser_cert = None

        self.browser_combo.connect("changed", self.on_browser_profile_changed)
        self.browser_listbox.connect("row-selected", self.on_browser_cert_selected)
        self.browser_import_button.connect("clicked", self.on_browser_import_clicked)
        self.browser_export_button.connect("clicked", self.on_browser_export_clicked)
        self.browser_delete_button.connect("clicked", self.on_browser_delete_clicked)

    # ------------------------------------------------------------------ #
    # Certificate listing
    # ------------------------------------------------------------------ #

    def load_certificates(self):
        for row in self.cert_listbox.get_children():
            self.cert_listbox.remove(row)

        for item in list_all_certificates():
            self.cert_listbox.add(self.create_certificate_row(item))

        self.cert_listbox.show_all()

    def load_browser_profiles(self):
        pass

    def create_certificate_row(self, item):
        row = Gtk.ListBoxRow()

        label = Gtk.Label(label=item.name, xalign=0)
        label.set_margin_top(6)
        label.set_margin_bottom(6)
        label.set_margin_start(10)
        label.set_margin_end(10)

        row.add(label)
        row.cert_item = item
        return row

    # ------------------------------------------------------------------ #
    # Signal handlers
    # ------------------------------------------------------------------ #

    def on_add_button_clicked(self, button):
        path = self.run_import_chooser()
        if path is None:
            return

        cert = load_certificate(path)
        if cert is None:
            self.show_error(
                _("Could not read certificate"),
                _("'{}' is not a valid PEM certificate.").format(path.name),
            )
            return

        self.show_certificate_details(path, cert)

    def run_import_chooser(self):
        response = self.import_chooser.run()
        filename = self.import_chooser.get_filename()
        self.import_chooser.hide()
        if response == Gtk.ResponseType.OK and filename:
            return Path(filename)
        return None

    def show_certificate_details(self, path, cert):
        info = cert_info(cert)
        self.details_values["file"].set_text(path.name)
        self.details_values["subject"].set_text(info["subject"])
        self.details_values["issuer"].set_text(info["issuer"])
        self.details_values["not_before"].set_text(info["not_before"])
        self.details_values["not_after"].set_text(info["not_after"])
        self.details_values["serial"].set_text(info["serial"])
        self.details_values["fingerprint"].set_text(info["fingerprint"])
        self.details_values["is_ca"].set_text(_("Yes") if info["is_ca"] else _("No"))
        self.details_values["status"].set_text(info["status"])
        self.set_warnings(info)

        response = self.cert_details_dialog.run()
        self.cert_details_dialog.hide()

        if response == Gtk.ResponseType.OK:
            self.show_error(
                _("Not implemented yet.."),
                _("TESTINGGG"),
            )

    def set_warnings(self, info):
        messages = []
        if info["status"] == "expired":
            messages.append(_("This certificate has expired."))
        elif info["status"] == "not_yet_valid":
            messages.append(_("This certificate is not valid yet."))
        if info["is_self_signed"] and info["is_ca"]:
            messages.append(
                _("Self-signed root CA. Trusting it means trusting every "
                  "certificate it signs.")
            )
        elif not info["is_ca"]:
            messages.append(_("This is not a CA certificate."))

        if messages:
            self.details_warning_label.set_markup(
                "<b>{}</b>".format("\n".join(messages))
            )
            self.details_warning_label.show()
        else:
            self.details_warning_label.hide()

    def show_error(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def on_delete_button_clicked(self, button):
        print("Delete button clicked")

    # BROWSER FUNCTIONS

    def on_browser_profile_changed(self, combo):
        pass

    def on_browser_cert_selected(self, listbox, row):
        pass

    def on_browser_import_clicked(self, button):
        pass

    def on_browser_export_clicked(self, button):
        pass


    def on_browser_delete_clicked(self, button):
        pass


    def on_refresh_button_clicked(self, button):
        self.load_certificates()
        self.load_browser_profiles()

    def on_menu_about_clicked(self, button):
        self.about_dialog.run()
        self.about_dialog.hide()

    def on_menu_settings_clicked(self, button):
        print("Settings button clicked")
