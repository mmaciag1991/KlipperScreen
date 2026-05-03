import logging
import subprocess

logger = logging.getLogger("KOS-Logs")

PANEL_TITLE = "Logi drukarki"

LOG_PATHS = {
    "klippy": "/home/pi/printer_data/logs/klippy.log",
    "moonraker": "/home/pi/printer_data/logs/moonraker.log",
    "crowsnest": "/home/pi/printer_data/logs/logs/crowsnest.log",
    "klipperscreen": "/home/pi/printer_data/logs/KlipperScreen.log",
    "octoeverywhere": "/home/pi/printer_data/logs/octoeverywhere.log",
    "mmu": "/home/pi/printer_data/logs/mmu.log",
}

DISPLAY_NAMES = {
    "klippy": "Klipper",
    "moonraker": "Moonraker",
    "crowsnest": "Crowsnest",
    "klipperscreen": "KlipperScreen",
    "mmu": "MMU",
}

LOG_SOURCES = list(LOG_PATHS.keys())


def read_log_tail(source: str, lines: int = 200) -> str:
    path = LOG_PATHS.get(source)

    if not path:
        return "Nieznane źródło logów"

    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), path],
            capture_output=True,
            text=True
        )

        return result.stdout if result.returncode == 0 else result.stderr

    except Exception as e:
        return f"Błąd odczytu logu: {e}"


try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, GLib, Pango

    class LogViewerPanel:
        REFRESH_INTERVAL = 3

        def __init__(self):
            self._current_source = "klippy"
            self._timer = None

        def build_ui(self):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

            # 🔥 FULL PANEL BEHAVIOR
            box.set_vexpand(True)
            box.set_hexpand(True)
            box.set_margin_top(0)
            box.set_margin_start(0)
            box.set_margin_end(0)
            box.set_margin_bottom(0)

            # TITLE
            title = Gtk.Label()
            title.set_markup(f"<b>{PANEL_TITLE}</b>")
            title.set_halign(Gtk.Align.CENTER)
            box.pack_start(title, False, False, 5)

            # TOP BAR
            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

            self.combo = Gtk.ComboBoxText()
            for src in LOG_SOURCES:
                self.combo.append_text(DISPLAY_NAMES.get(src, src))

            self.combo.set_active(0)
            self.combo.connect("changed", self._on_source)

            btn = Gtk.Button(label="Odśwież")
            btn.connect("clicked", self._refresh)

            top.pack_start(Gtk.Label(label="Źródło:"), False, False, 0)
            top.pack_start(self.combo, True, True, 0)
            top.pack_start(btn, False, False, 0)

            box.pack_start(top, False, False, 5)

            # HEADER
            self.header = Gtk.Label()
            self.header.set_halign(Gtk.Align.START)
            box.pack_start(self.header, False, False, 3)

            # SCROLL AREA
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

            # 🔥 IMPORTANT: FILL PANEL
            scroll.set_vexpand(True)
            scroll.set_hexpand(True)

            self.text = Gtk.TextView()
            self.text.set_editable(False)
            self.text.set_cursor_visible(False)

            # FILL TEXT AREA TOO
            self.text.set_vexpand(True)
            self.text.set_hexpand(True)

            font = Pango.FontDescription("monospace 9")
            self.text.override_font(font)

            self.buf = self.text.get_buffer()

            # COLORS
            self.tag_err = self.buf.create_tag("e", foreground="#ff4d4d")
            self.tag_warn = self.buf.create_tag("w", foreground="#ffaa00")
            self.tag_info = self.buf.create_tag("i", foreground="#66ccff")
            self.tag_dbg = self.buf.create_tag("d", foreground="#999999")

            scroll.add(self.text)
            box.pack_start(scroll, True, True, 0)

            self.scroll = scroll

            self._load()
            self._start_timer()

            return box

        # -------------------------
        # TIMER
        # -------------------------
        def _start_timer(self):
            if self._timer:
                GLib.source_remove(self._timer)

            self._timer = GLib.timeout_add_seconds(
                self.REFRESH_INTERVAL,
                self._tick
            )

        def _tick(self):
            self._load()
            return True

        # -------------------------
        # EVENTS
        # -------------------------
        def _on_source(self, combo):
            self._current_source = LOG_SOURCES[combo.get_active()]
            self._load()

        def _refresh(self, _):
            self._load()

        # -------------------------
        # LOAD LOG
        # -------------------------
        def _load(self):
            text = read_log_tail(self._current_source)

            self.buf.set_text("")
            lines = text.splitlines()

            for line in lines:
                self._append(line)

            self.header.set_text(
                f"{DISPLAY_NAMES.get(self._current_source)} — {len(lines)} linii"
            )

            GLib.idle_add(self._scroll_bottom)

        def _append(self, line):
            it = self.buf.get_end_iter()
            u = line.upper()

            tag = None
            if "ERROR" in u:
                tag = self.tag_err
            elif "WARN" in u:
                tag = self.tag_warn
            elif "INFO" in u:
                tag = self.tag_info
            elif "DEBUG" in u:
                tag = self.tag_dbg

            if tag:
                self.buf.insert_with_tags(it, line + "\n", tag)
            else:
                self.buf.insert(it, line + "\n")

        def _scroll_bottom(self):
            adj = self.scroll.get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())
            return False

except ImportError:
    logger.warning("GTK nie jest dostępne")


# -------------------------
# KLIPPERSCREEN PANEL
# -------------------------
from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    def __init__(self, screen, title):
        super().__init__(screen, title or PANEL_TITLE)

        try:
            ui = LogViewerPanel()
            self.content.add(ui.build_ui())

        except Exception as e:
            logger.error(f"Błąd panelu: {e}")

            try:
                import gi
                gi.require_version("Gtk", "3.0")
                from gi.repository import Gtk

                err = Gtk.Label(label=f"Błąd:\n{e}")
                err.set_line_wrap(True)
                self.content.add(err)
            except:
                pass