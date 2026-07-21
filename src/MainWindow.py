import os
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import locale
from locale import gettext as _

from pathlib import Path

from system import certificate_info, system_cert_store
from browsers import browser_cert_store

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
        self.selected_system_item = None
        self.add_button.connect("clicked", self.on_add_button_clicked)
        self.delete_button.connect("clicked", self.on_delete_button_clicked)
        self.cert_listbox.connect("row-selected", self.on_system_cert_selected)
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

        self.selected_system_item = None
        self.delete_button.set_sensitive(False)

        for item in system_cert_store.list_all_certificates():
            self.cert_listbox.add(self.create_certificate_row(item))

        self.cert_listbox.show_all()

    def load_browser_profiles(self):
        self.browser_profiles = browser_cert_store.list_profiles()
        self.browser_combo.remove_all()
        for profile in self.browser_profiles:
            self.browser_combo.append_text(profile.label)
        if self.browser_profiles:
            self.browser_combo.set_active(0)

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

        cert = system_cert_store.load_certificate(path)
        if cert is None:
            self.show_error(
                _("Could not read certificate"),
                _("'{}' is not a valid PEM certificate.").format(path.name),
            )
            return

        if not self.show_certificate_details(path, cert):
            return

        if system_cert_store.install_certificate(path):
            self.load_certificates()
            self.show_info(
                _("Certificate installed"),
                _("'{}' was added to the system trust store.").format(
                    path.name
                ),
            )
        else:
            self.show_error(
                _("Install failed"),
                _("Could not install '{}'.").format(path.name),
            )

    def run_import_chooser(self):
        response = self.import_chooser.run()
        filename = self.import_chooser.get_filename()
        self.import_chooser.hide()
        if response == Gtk.ResponseType.OK and filename:
            return Path(filename)
        return None

    def show_certificate_details(self, path, cert):
        info = certificate_info.cert_info(cert)
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
        return response == Gtk.ResponseType.OK

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

    def confirm(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=title,
        )
        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def show_info(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.CLOSE,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def on_system_cert_selected(self, listbox, row):
        self.selected_system_item = getattr(row, "cert_item", None) if row else None
        # Only user added certs can be removed
        removable = (
            self.selected_system_item is not None
            and self.selected_system_item.source == "user"
        )
        self.delete_button.set_sensitive(removable)

    def on_delete_button_clicked(self, button):
        item = self.selected_system_item
        if item is None or item.source != "user":
            return

        if not self.confirm(
            _("Delete certificate?"),
            _("'{}' will be removed from the system trust store.").format(
                item.name
            ),
        ):
            return

        if system_cert_store.remove_certificate(item.removable_name):
            self.load_certificates()
            self.delete_button.set_sensitive(False)
        else:
            self.show_error(
                _("Delete failed"),
                _("Could not delete '{}'.").format(item.name),
            )

    # ------------------------------------------------------------------ #
    # Browser Page Functions
    # ------------------------------------------------------------------ #

    def on_browser_profile_changed(self, combo):
        for row in self.browser_listbox.get_children():
            self.browser_listbox.remove(row)

        # Rows are gone, reset old selection
        self.selected_browser_cert = None
        self.browser_export_button.set_sensitive(False)
        self.browser_delete_button.set_sensitive(False)

        index = combo.get_active()
        if index < 0 or index >= len(self.browser_profiles):
            return
        profile = self.browser_profiles[index]

        for cert in browser_cert_store.list_certificates(profile):
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=cert.nickname, xalign=0)
            label.set_margin_top(6)
            label.set_margin_bottom(6)
            label.set_margin_start(10)
            label.set_margin_end(10)
            row.add(label)
            row.browser_cert = cert
            self.browser_listbox.add(row)

        self.browser_listbox.show_all()

    def on_browser_cert_selected(self, listbox, row):
        self.selected_browser_cert = getattr(row, "browser_cert", None) if row else None
        has_selection = self.selected_browser_cert is not None
        self.browser_export_button.set_sensitive(has_selection)
        self.browser_delete_button.set_sensitive(has_selection)

    def on_browser_import_clicked(self, button):
        index = self.browser_combo.get_active()
        if index < 0 or index >= len(self.browser_profiles):
            return
        profile = self.browser_profiles[index]

        path = self.run_import_chooser()
        if path is None:
            return

        cert = system_cert_store.load_certificate(path)
        if cert is None:
            self.show_error(
                _("Could not read certificate"),
                _("'{}' is not a valid PEM certificate.").format(path.name),
            )
            return

        if not certificate_info.cert_info(cert)["is_ca"]:
            self.show_error(
                _("Not a CA certificate"),
                _("Only CA certificates can be added to the browser "
                  "trust store."),
            )
            return

        if not self.show_certificate_details(path, cert):
            return

        nickname = path.stem
        existing = {c.nickname for c in browser_cert_store.list_certificates(profile)}
        if nickname in existing:
            self.show_error(
                _("Certificate already exists"),
                _("'{}' is already in this profile.").format(nickname),
            )
            return

        if browser_cert_store.install_certificate(profile, path, nickname):
            self.on_browser_profile_changed(self.browser_combo)
            self.show_info(
                _("Certificate added"),
                _("'{}' was added to {}.").format(nickname, profile.label),
            )
        else:
            self.show_error(
                _("Import failed"),
                _("Could not import '{}'.").format(path.name),
            )

    def on_browser_export_clicked(self, button):
        if not self.selected_browser_cert:
            return
        cert = self.selected_browser_cert
        pem = browser_cert_store.export_certificate_pem(cert.profile, cert.nickname)
        if pem is None:
            self.show_error(_("Export failed"), _("Could not read the certificate."))
            return

        dialog = Gtk.FileChooserDialog(
            title=_("Export Certificate"),
            transient_for=self.window,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            _("Cancel"), Gtk.ResponseType.CANCEL,
            _("Save"), Gtk.ResponseType.OK,
        )
        dialog.set_do_overwrite_confirmation(True)
        # Nicknames may contain '/', which is invalid in file names
        dialog.set_current_name(cert.nickname.replace("/", "_") + ".pem")

        response = dialog.run()
        filename = dialog.get_filename()
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not filename:
            return

        try:
            Path(filename).write_text(pem)
        except OSError as error:
            self.show_error(_("Export failed"), str(error))
            return

        self.show_info(
            _("Certificate exported"),
            _("Saved to {}.").format(filename),
        )

    def on_browser_delete_clicked(self, button):
        if not self.selected_browser_cert:
            return
        cert = self.selected_browser_cert

        if not self.confirm(
            _("Delete certificate?"),
            _("'{}' will be removed from {}. Websites signed by it will "
              "no longer be trusted by this browser.").format(
                cert.nickname, cert.profile.label
            ),
        ):
            return

        if browser_cert_store.delete_certificate(cert.profile, cert.nickname):
            self.on_browser_profile_changed(self.browser_combo)
        else:
            self.show_error(
                _("Delete failed"),
                _("Could not delete '{}'.").format(cert.nickname),
            )

    def on_refresh_button_clicked(self, button):
        self.load_certificates()
        self.load_browser_profiles()

    def on_menu_about_clicked(self, button):
        self.about_dialog.run()
        self.about_dialog.hide()

    def on_menu_settings_clicked(self, button):
        print("Settings button clicked")
