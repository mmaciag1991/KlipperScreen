import logging
import random
import gi
import time

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango

from ks_includes.KlippyGcodes import KlippyGcodes
from ks_includes.screen_panel import ScreenPanel



class Panel(ScreenPanel):

    def __init__(self, screen, title):

        super().__init__(screen, title)
        self.menu = ['dev_panel']

        self.process_index: int = 0

        self.current_extruder = self._printer.get_stat("toolhead", "EXTRUDER")

        probe_sensors_list = ["probe"]
        filament_sensors_list = (
                self._printer.get_filament_sensors()
                + [f"mmu_pre_gate_{i}" for i in range(8)]
                + ["mmu_gate", "extruder"]
        )
        endstops_sensors_list = ["Endstop X", "Endstop Y", "Endstop Z"]

        spool_sensors_grid = Gtk.Grid()
        self.arrange_grid(spool_sensors_grid)

        endstop_sensors_grid = Gtk.Grid()
        self.arrange_grid(endstop_sensors_grid)

        probe_sensors_grid = Gtk.Grid()
        self.arrange_grid(probe_sensors_grid)

        self.limit: int = 15

        self.loop(filament_sensors_list, spool_sensors_grid)
        self.loop(endstops_sensors_list, endstop_sensors_grid)
        self.loop(probe_sensors_list, probe_sensors_grid)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_hexpand(True)
        main_box.set_vexpand(True)


        main_box.pack_start(Gtk.Label("MMU / Filament"), False, False, 5)
        main_box.pack_start(spool_sensors_grid, False, False, 0)

        main_box.pack_start(Gtk.Label("Endstops"), False, False, 5)
        main_box.pack_start(endstop_sensors_grid, False, False, 0)

        main_box.pack_start(Gtk.Label("Probe"), False, False, 5)
        main_box.pack_start(probe_sensors_grid, False, False, 0)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        
        scrolled.add_with_viewport(main_box)
        
        self.content.set_hexpand(True)
        self.content.set_vexpand(True)
        
        self.content.add(scrolled)
        

    def loop(self, sensor_list, sensor_grid):
        if len(sensor_list) > 0:
            for number_index, x in enumerate(sensor_list):
                if number_index > self.limit:
                    break
                self.labels[x] = {
                    'label': Gtk.Label(f"{x}"),
                    'box': Gtk.Box()
                }
                self.labels[x]['box'].pack_start(self.labels[x]['label'], True, True, 5)

                sensor_grid.attach(Gtk.Label(f"\n\t{x.replace('_', ' ').title()}\t\n"), 0, number_index, 1, 1)
                sensor_grid.attach(self.labels[x]['box'], 1, number_index, 1, 1)

    def arrange_grid(self, grid):
        grid.set_halign(Gtk.Align.BASELINE)
        grid.set_valign(Gtk.Align.BASELINE)

    def send_query_gcodes(self):
        query_endstops_cmd = "query_endstops"
        query_probe_cmd = "query_probe"
        self._screen._ws.klippy.gcode_script(query_endstops_cmd)
        self._screen._ws.klippy.gcode_script(query_probe_cmd)

    def process_update(self, action, data):
        
        self.process_index += 1
        if self.process_index % 6 == 0:
            self.send_query_gcodes()
            self.process_index = 0

        def style_box(label, style, remove: bool):
            if remove:
                self.labels[label]['box'].get_style_context().remove_class(style)
            else:
                self.labels[label]['box'].get_style_context().add_class(style)

        for sensor in self.labels.keys():
            if f"{sensor}:TRIGGERED" in data:
                state = "Uruchomiony"
                self.labels[sensor]['label'].set_text(f"{state}")
                style_box(sensor, "filament_sensor_empty", remove=True)
                style_box(sensor, "filament_sensor_detected", remove=False)

            elif f"{sensor}:open" in data:
                state = "Nieuruchomiony"
                self.labels[sensor]['label'].set_text(f"{state}")
                style_box(sensor, "filament_sensor_detected", remove=True)
                style_box(sensor, "filament_sensor_empty", remove=False)

        

        def update_endstop_label(e, data, startswith="Endstop "):
            if 'endstop' in startswith.lower():
                label = f"{startswith}{e.upper()}"
            else:
                label = f"{e.replace('_', ' ').title()}"
            if f'{e}:open' in data:
                state = "Nieuruchomiony"
                self.labels[label]['label'].set_text(f"{state}")
                style_box(label, "filament_sensor_detected", remove=True)
                style_box(label, "filament_sensor_empty", remove=False)
            if f'{e}:TRIGGERED' in data:
                state = "Uruchomiony"
                self.labels[sensor]['label'].set_text(f"{state}")
                style_box(label, "filament_sensor_empty", remove=True)
                style_box(label, "filament_sensor_detected", remove=False)

        if action == "notify_gcode_response":

            if 'probe: ' in data:
                if 'probe: open' in data:
                    state = "Nieuruchomiony"
                    self.labels[sensor]['label'].set_text(f"{state}")
                    style_box("probe", "filament_sensor_empty", remove=True)
                    style_box("probe", "filament_sensor_detected", remove=False)
                if 'probe: TRIGGERED' in data:
                    state = "Uruchomiony"
                    self.labels[sensor]['label'].set_text(f"{state}")
                    style_box("probe", "filament_sensor_detected", remove=True)
                    style_box("probe", "filament_sensor_empty", remove=False)

            update_endstop_label(e="x", data=data)
            update_endstop_label(e="y", data=data)
            update_endstop_label(e="z", data=data)

        if action == "notify_busy":
            return
        if action != "notify_status_update":
            return

        for x in self._printer.get_filament_sensors():
            if x in data:
                # if 'enabled' in data[x]:
                    # self._printer.set_dev_stat(x, "enabled", data[x]['enabled'])
                if 'filament_detected' in data[x]:
                    # self._printer.set_dev_stat(x, "filament_detected", data[x]['filament_detected'])
                    if self._printer.get_stat(x, "enabled"):
                        if data[x]['filament_detected']:
                            state = "Uruchomiony"
                            self.labels[x]['label'].set_text(f"{state}")
                            style_box(x, "filament_sensor_empty", remove=True)
                            style_box(x, "filament_sensor_detected", remove=False)
                        else:
                            state = "Nieuruchomiony"
                            self.labels[x]['label'].set_text(f"{state}")
                            style_box(x, "filament_sensor_detected", remove=True)
                            style_box(x, "filament_sensor_empty", remove=False)
                logging.info(f"{x}: {self._printer.get_stat(x)}")