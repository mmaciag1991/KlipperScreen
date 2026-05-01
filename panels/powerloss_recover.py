# -*- coding: utf-8 -*-
import logging
import gi
import os
import configparser

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango, GdkPixbuf
from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):

    def __init__(self, screen, title):
        super().__init__(screen, title)

        self.menu = ['powerloss_recover']

        # 🔥 TWOJA ŚCIEŻKA MMU VARS
        self.print_state_file = os.path.expanduser(
            "~/printer_data/config/mmu/mmu_vars.cfg"
        )

        self.filename = None
        self.resume_button = None
        self.tip_label = None

        self.width = self._gtk.content_width
        self.height = self._gtk.content_height

        self.preview_size = min(self.width // 3, self.height // 2)
        self.margin = 20

         # ================= MAIN GRID =================
        main = Gtk.Grid()
        main.set_column_spacing(30)
        main.set_row_spacing(10)
        main.set_hexpand(True)
        main.set_vexpand(True)
        
        # =========================================================
        # LEFT SIDE (50%) - PREVIEW
        # =========================================================
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        left.set_hexpand(True)
        left.set_vexpand(True)
        
        preview_frame = Gtk.Frame()
        preview_frame.set_shadow_type(Gtk.ShadowType.IN)
        
        # klucz: wymuszenie 50% szerokości
        left_box = Gtk.Box()
        left_box.set_hexpand(True)
        left_box.set_vexpand(True)
        left_box.set_size_request(self.width // 2, -1)
        
        self.preview_image = Gtk.Image()
        self.preview_image.set_pixel_size(self.preview_size)
        
        left_box.pack_start(self.preview_image, True, True, 10)
        preview_frame.add(left_box)
        
        self.resume_button = self._gtk.Button("resume", _("Resume"), "color2")
        self.resume_button.set_size_request(-1, 60)
        self.resume_button.connect("clicked", self.resume_print)
        
        left.pack_start(preview_frame, True, True, 0)
        left.pack_start(self.resume_button, False, False, 0)
        
        main.attach(left, 0, 0, 1, 1)
        
        # =========================================================
        # RIGHT SIDE (50%) - INFO
        # =========================================================
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        right.set_hexpand(True)
        right.set_vexpand(True)
        
        self.info = Gtk.Label()
        self.info.set_xalign(0)
        self.info.set_yalign(0)
        
        # 🔥 WAŻNE: większa czytelność
      
        self.info.set_line_wrap(True)
        self.info.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.info.set_xalign(0)
        self.info.set_width_chars(10)
        self.info.set_line_wrap(True)
        self.info.set_justify(Gtk.Justification.LEFT)
        
        right.pack_start(self.info, True, True, 0)
        
        self.tip_label = Gtk.Label()
        self.tip_label.set_markup(
            "<span foreground='orange' size='12000'>Gotowe do wznowienia druku</span>"
        )
        
        right.pack_start(self.tip_label, False, False, 0)
        
        main.attach(right, 1, 0, 1, 1)
        
        self.content.add(main)

        self.load()

    def activate(self):
        """Called every time panel is shown"""
        logging.info("PLR panel activate → reloading vars")

        self.load()

    def set_state(self, active):
        self.resume_button.set_sensitive(active)
    
        if not active:
            self.tip_label.set_markup(
                "<span foreground='red'>Brak aktywnej konfiguracji wznowienia</span>"
            )
        else:
            self.tip_label.set_markup(
                "<span foreground='orange'>Możesz wznowić wydruk</span>"
            )
    # =========================================================
    # LOAD MMU VARS
    # =========================================================
    def load(self):
        if not os.path.exists(self.print_state_file):
            self.info.set_text("Brak mmu_vars.cfg")
            self.resume_button.set_sensitive(False)
            return

        cfg = configparser.ConfigParser()
        cfg.read(self.print_state_file)

        try:
            v = cfg["Variables"]

            self.filename = v.get("plr_file", None)
            z = v.getfloat("plr_z_height", 0)
            bed = v.getfloat("plr_bed_temp", 0)
            ext = v.getfloat("plr_extruder_temp", 0)
            fan = v.getfloat("plr_fan_speed", 0)
            plr_active = v.get("plr_active", fallback="False")

            if plr_active == "True":
                self.set_state(True)
            else:
                self.set_state(False)
                
            self.info.set_text(
                f"""
PLIK: {self.filename}

Z: {z}

STÓŁ: {bed}

EXTRUDER: {ext}

WENTYLATOR: {fan}
"""
            )

            self.load_preview()

        except Exception as e:
            logging.exception(e)
            self.info.set_text("Błąd mmu_vars.cfg")
            self.resume_button.set_sensitive(False)

    # =========================================================
    # PREVIEW (.thumbs)
    # =========================================================
    def load_preview(self):
        if not self.filename:
            return

        gcode_dir = os.path.expanduser("~/printer_data/gcodes")
        thumbs = os.path.join(gcode_dir, ".thumbs")

        base = os.path.basename(self.filename).split(".gcode")[0]

        for size in ["512x512", "32x32", "64x64"]:
            path = os.path.join(thumbs, f"{base}-{size}.png")
            if os.path.exists(path):
                pix = self.load_scaled_thumbnail(path)
                self.preview_image.set_from_pixbuf(pix)
                return

        self.preview_image.set_from_icon_name("image-missing", 4)
    def load_scaled_thumbnail(self, path):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
    
            target = 256
    
            width = pixbuf.get_width()
            height = pixbuf.get_height()
    
            scale = min(target / width, target / height)
    
            new_w = int(width * scale)
            new_h = int(height * scale)
    
            scaled = pixbuf.scale_simple(
                new_w,
                new_h,
                GdkPixbuf.InterpType.BILINEAR
            )
    
            return scaled
    
        except Exception as e:
            logging.error(f"Thumbnail scale error: {e}")
            return None
    # =========================================================
    # RESUME (PRUSA STYLE FLOW)
    # =========================================================
    def resume_print(self, widget):

        self._screen._send_action(
            widget,
            "printer.gcode.script",
            {"script": "PLR_RESUME"}
        )
    
        self._screen.state_printing()