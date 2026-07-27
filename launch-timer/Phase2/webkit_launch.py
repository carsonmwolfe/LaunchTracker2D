#!/usr/bin/env python3
"""Lightweight WebKit2GTK kiosk launcher — replaces Chromium for Pi 3 A+."""
import gi, sys

gi.require_version('WebKit2', '4.1')
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, WebKit2, Gdk

url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:5001/'

win = Gtk.Window()
win.set_title('RangeTrack')
win.set_decorated(False)
win.fullscreen()
win.connect('destroy', Gtk.main_quit)

settings = WebKit2.Settings()
settings.set_enable_accelerated_2d_canvas(True)
settings.set_enable_webgl(True)
settings.set_enable_smooth_scrolling(False)
settings.set_enable_write_console_messages_to_stdout(True)
settings.set_allow_file_access_from_file_urls(True)
settings.set_allow_universal_access_from_file_urls(True)
try:
    settings.set_hardware_acceleration_policy(WebKit2.HardwareAccelerationPolicy.ALWAYS)
except AttributeError:
    pass

wv = WebKit2.WebView()
wv.set_settings(settings)
wv.set_background_color(Gdk.RGBA(10/255, 14/255, 20/255, 1.0))
wv.load_uri(url)

win.add(wv)
win.show_all()

blank = Gdk.Cursor.new_for_display(Gdk.Display.get_default(), Gdk.CursorType.BLANK_CURSOR)
win.get_window().set_cursor(blank)

Gtk.main()
