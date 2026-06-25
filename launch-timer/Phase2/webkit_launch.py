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

wv = WebKit2.WebView()
wv.load_uri(url)

win.add(wv)
win.show_all()

blank = Gdk.Cursor.new_for_display(Gdk.Display.get_default(), Gdk.CursorType.BLANK_CURSOR)
win.get_window().set_cursor(blank)

Gtk.main()
