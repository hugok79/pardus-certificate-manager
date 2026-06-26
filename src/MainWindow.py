import os
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import locale
from locale import gettext as _

from system.certificate_store import list_all_certificates

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

        # Signals
        self.add_button.connect("clicked", self.on_add_button_clicked)
        self.delete_button.connect("clicked", self.on_delete_button_clicked)
        self.refresh_button.connect("clicked", self.on_refresh_button_clicked)
        self.menu_about.connect("clicked", self.on_menu_about_clicked)
        self.menu_settings.connect("clicked", self.on_menu_settings_clicked)

    # ------------------------------------------------------------------ #
    # Certificate listing
    # ------------------------------------------------------------------ #

    def load_certificates(self):
        for row in self.cert_listbox.get_children():
            self.cert_listbox.remove(row)

        for item in list_all_certificates():
            self.cert_listbox.add(self.create_certificate_row(item))

        self.cert_listbox.show_all()

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
        # certificate_parser.py
        print("Add button clicked")

    def on_delete_button_clicked(self, button):
        print("Delete button clicked")

    def on_refresh_button_clicked(self, button):
        self.load_certificates()

    def on_menu_about_clicked(self, button):
        self.about_dialog.run()
        self.about_dialog.hide()

    def on_menu_settings_clicked(self, button):
        print("Settings button clicked")
