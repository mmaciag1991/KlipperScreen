import json
import logging
import os

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf, Gdk, Pango
from jinja2 import Template
from datetime import datetime
from ks_includes.screen_panel import ScreenPanel
from ks_includes.KlippyGtk import find_widget
from ks_includes.widgets.flowboxchild_extended import PrintListItem
STATIC_CONSUMABLES = {
    'supplier_select': ('Bambu Lab', 'Generic', 'Polymaker', 'Overture', 'eSUN'),
    'consumables_select': ('PLA', 'PETH', 'TPU'),
    'diameter_select': ('0.75mm','1.75mm')
}

#msgfmt -o /home/gsq/PycharmProjects/HuaFu-KlipperScreen/ks_includes/locales/zh_CN/LC_MESSAGES/KlipperScreen.mo /home/gsq/PycharmProjects/HuaFu-KlipperScreen/ks_includes/locales/zh_CN/LC_MESSAGES/KlipperScreen.po
#pip3 install sdbus --break-system-packages

from panels.print import (refresh_loading,
                                    cancel,
                                    set_loading,
                                    pause_confirm,
                                    update_time_left,
                                    print_time_format,
                                    create_print_file_list_item)
from panels.printer_control import (move,
                                  direction_home,
                                  change_distance,
                                  on_digit_clicked,
                                  change_target_temp,
                                  change_print_speed,
                                  update_print_speed_message,
                                  update_speed_button,
                                  change_fan_value)
from panels.edit_consumables import consumables_dialog,change_consumables_button,check_min_temp,consumables_confirm,change_extruder
from panels.calibration import (bed_mesh_calibration,
                                  init_xyz_offset,
                                  update_position,
                                  buttons_calibrating,
                                  buttons_not_calibrating,
                                  start_z_calibration,
                                  confrim_calibration,
                                  cancle_calibration)
from panels.settings_menu import dialog_message
from panels.macro_command import cut,stop_chamber_temperature,clean_nozzle,turn_on_each_detection_bed,turn_off_each_detection_bed
from panels.firmware_information import update_system_info
from panels.wifi import init_panel,on_refresh_clicked,on_wifi_switch_toggled


class Panel(ScreenPanel):

    def __init__(self, screen, title, items=None, **panel_args):
        super().__init__(screen, title)
        self.items = items
        self.loading_msg = _('Loading...')
        self.j2_data = self._printer.get_printer_status_data()
        self.create_menu_items(title,**panel_args)
        self.scroll = self._gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.vertical_mode = self._screen.vertical_mode
        if "flowbox" in self.labels:
            self._screen._ws.klippy.get_dir_info(self.load_files, self.cur_directory)


    def activate(self):
        self.j2_data = self._printer.get_printer_status_data()
        self.add_content()

    def add_content(self):
        for child in self.scroll.get_children():
            self.scroll.remove(child)
        # self.scroll.add(self.arrangeMenuItems(self.items))
        if not self.content.get_children():
            self.content.add(self.scroll)


    def arrangeMenuItems(self, items, columns=None, expand_last=False):
        print("arrangeMenuItems")



    def create_menu_items(self,panel_name,fileinfo=None,father=None,select_extruder=None):
        """
            创建主界面 下半部分元素
        :return:
        """
        parent_grid = Gtk.Grid()
        self.counter = i = 0
        self.create_radionButton = False
        self.radioButton = {}
        self.entry = {}
        self.percentage_progress = 0.0;
        self.cur_directory = 'gcodes'
        self.list_mode = True
        self.time_24 = self._config.get_main_config().getboolean("24htime", True)
        self.list_button_size = self._gtk.img_scale * self.bts
        self.thumbsize = self._gtk.img_scale * self._gtk.button_image_scale * 2.5
        self.select_extruder="T0: "
        self.is_printing=False
        self.filename = None
        self.file_metadata = None
        self.grid = {}
        self.box = {}
        self.switch ={}
        self.wifi_switch = None
        self.total_layers = 0
        self.current_layer = 0
        self.print_state = ''
        self.init_panel = True
        self.change_item = ['print_busy',
                            'fen_model','speed_control_model','chassis_temperature', 'heater_bed_temperature', 'extruder_temperature', 'extruder1_temperature',
                            'percentage_progress','print_layers','print_speed','remaining_time','floor_height_progress',
                            'print_modeling_graphics', 'print_file_name', 'print_state','pause_button','cancel_button',
                            't0_extruder_consumables_control',
                            'start_z_calibration','raise_heater_bed','reduce_heater_bed','confirm','cancel',
                            'z_value','old_z_value','new_z_value',
                            'system_version','network_address','ip_address','mac_address',
                            'wifi_ip','reload_wifi']
        self.buttons = {}
        if panel_name == "sport_control" or panel_name == "z_offset_calibration":
            self.distance=1
            self.buttons['distance_button']=[]
        if panel_name == "control_consumables":
            self.labels["length"]=10
            self.buttons['length_button']=[]
            self.labels["speed"] = 10
            self.buttons['speed_button'] = []
        if panel_name == "speed_control":
            self.print_speed = 100
            self.buttons["print_speed"] = []
        while i< len(self.items):
            key = list(self.items[i])[0]
            item = self.items[i][key]
            if self._screen.vertical_mode:
                parent_grid.attach(self.create_child_items(i,panel_name,fileinfo,father,select_extruder),
                        int(item['v_column']),
                        int(item['v_row']),
                        int(item['v_columnspan']),
                        int(item['v_rowspan']))
            else:
                parent_grid.attach(self.create_child_items(i,panel_name,fileinfo,father,select_extruder),
                        int(item['column']),
                        int(item['row']),
                        int(item['columnspan']),
                        int(item['rowspan']))
            i = self.counter
        if(panel_name is not None):
            parent_grid.set_name(panel_name)
        if(panel_name in ("printer_control_menu", "messages_menu")):
            if self._screen.vertical_mode:
                parent_grid.set_row_homogeneous(False)
            else:
                parent_grid.set_row_homogeneous(True)

        if panel_name == "print_file_list":
            self._screen._ws.klippy.get_dir_info(self.load_files, self.cur_directory)
        if panel_name == "print_menu" and self.filename is not None :
            self.init_file_data(True)
        if panel_name == 'firmware_information':
            update_system_info(self)
        if panel_name == "wifi" :
            init_panel(self)
        self.labels['parent_grid'] = parent_grid

        #初始化Z偏移校准数据
        if panel_name == "z_offset_calibration":
            init_xyz_offset(self)
        # self.content.add(parent_grid)

    def create_child_items(self,i,panel_name,fileinfo=None,father=None,select_extruder=None):
        self.counter =i
        key = list(self.items[i])[0]
        key_array=key.split(' ')
        current_key=key_array[len(key_array)-1]
        item = self.items[i][key]
        item_control_name = None

        if(item['type']=="Image"):
            self.counter += 1
            item_control_name = Gtk.Image()
            item_control_name.set_name(current_key)
            image = self._screen.env.from_string(item['src']).render(self.j2_data) if item['src'] else None
            width = int(self._screen.env.from_string(item['width']).render(self.j2_data) if item['width'] else None)
            height = int(self._screen.env.from_string(item['height']).render(self.j2_data) if item['height'] else None)
            if self._screen.vertical_mode:
                width = int(self._screen.env.from_string(item['v_width']).render(self.j2_data) if item['v_width'] else None)
                height = int(self._screen.env.from_string(item['v_height']).render(self.j2_data) if item['v_height'] else None)
            pixbuf = ''
            if fileinfo is not None and "path" not in  fileinfo and  current_key in self.change_item:
                pixbuf = self.get_file_image(fileinfo["path"], height, width, False)
                item_control_name = Gtk.Image.new_from_pixbuf(pixbuf)
            else:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(image)
                scaled_pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
                item_control_name.set_from_pixbuf(scaled_pixbuf)

            if current_key == 'print_modeling_graphics':
                self.labels[current_key]=item_control_name
                return self.labels[current_key]

        elif(item['type']=="Button"):
            self.counter += 1
            value = self._screen.env.from_string(item['value']).render(self.j2_data) if item['value'] else None
            style = self._screen.env.from_string(item['style']).render(self.j2_data) if item['style'] else None
            icon = self._screen.env.from_string(item['icon']).render(self.j2_data) if item['icon'] else None
            width = self._screen.env.from_string(item['width']).render(self.j2_data) if item['width'] else None
            height = self._screen.env.from_string(item['height']).render(self.j2_data) if item['height'] else None
            position = self._screen.env.from_string(item['position']).render(self.j2_data) if item['position'] else None
            button_width = self._screen.env.from_string(item['button_width']).render(self.j2_data) if item['button_width'] else None
            button_height = self._screen.env.from_string(item['button_height']).render(self.j2_data) if item['button_height'] else None
            hexpand = self._screen.env.from_string(item['hexpand']).render(self.j2_data) if item['hexpand'] else None
            vexpand = self._screen.env.from_string(item['vexpand']).render(self.j2_data) if item['vexpand'] else None
            if self._screen.vertical_mode:
                width = self._screen.env.from_string(item['v_width']).render(self.j2_data) if item['v_width'] else None
                height = self._screen.env.from_string(item['v_height']).render(self.j2_data) if item['v_height'] else None
                button_width = self._screen.env.from_string(item['v_button_width']).render(self.j2_data) if item['v_button_width'] else None
                button_height = self._screen.env.from_string(item['v_button_height']).render(self.j2_data) if item['v_button_height'] else None
            item_control_name = self._gtk.Button(icon,value,style,width,height,hexpand,vexpand,button_width,button_height,position)
            parameter_item = {
                "panel": item["panel"],
                "fileinfo": fileinfo,
                "father":panel_name,
                "icon": None
            }
            if (item["panel"] != None and item["panel"] == 'print_menu') and father !='print_menu':
                item_control_name.connect("clicked", print_start, parameter_item)
            if item["panel"] != None:
                # item_control_name.connect("clicked", self.menu_item_clicked, parameter_item)
                item_control_name.connect("clicked", self._screen.jump_rotor_page, parameter_item)
            elif(current_key == 'go_back'):
                item_control_name.connect("clicked", self._screen._menu_go_back)
            elif(item['method'] == 'show_dialog'):
                item_control_name.connect("clicked", self.show_dialog,current_key)
            elif(item['method'] == 'consumables_dialog'):
                # current_key :t1_extruder_consumables_control
                # item_control_name.connect("clicked", consumables_dialog,self,current_key)
                item_control_name.connect("clicked", consumables_confirm,2,None,self,None,current_key)
            elif(item['method'] == 'on_digit_clicked'):
                #panel_name extruder_temperature chassis_temperature heater_bed_temperature
                item_control_name.connect("clicked", on_digit_clicked, self, value, panel_name)
            elif(item['method'] == 'set_nozzle_type'):
                item_control_name.connect("clicked", self.set_nozzle_type)
            elif (item['method'] == 'refresh_loading'):
                item_control_name.connect("clicked", refresh_loading,self)
            elif (item['method'] == 'cancel_confirm'):
                item_control_name.connect("clicked", cancel,self)
            elif (item['method'] == 'pause_confirm'):
                item_control_name.connect("clicked", pause_confirm,self)
            elif (item['method'] == 'change_target_temp'):
                #更改腔温 热床温度
                #panel_name extruder_temperature chassis_temperature heater_bed_temperature
                item_control_name.connect("clicked", change_target_temp,self,panel_name,value)
            elif (item['method'] == 'change_print_speed'):
                item_control_name.connect("clicked", change_print_speed,self,value)
            elif (item['method'] == 'change_fan_value'):
                item_control_name.connect("clicked", change_fan_value,self)
            elif (item['method'] == 'move'):
                item_control_name.connect("clicked", move,self,value)
            elif (item['method'] == 'change_distance'):
                item_control_name.connect("clicked", change_distance,self,value)
            elif (item['method'] == 'direction_home'):
                item_control_name.connect("clicked", direction_home,self,value)
            elif (item['method'] == 'change_consumables_length'):
                item_control_name.connect("clicked", change_consumables_button,self,'length',value)
            elif (item['method'] == 'change_consumables_speed'):
                item_control_name.connect("clicked", change_consumables_button,self,'speed',value)
            elif (item['method'] == 'check_min_temp'):
                item_control_name.connect("clicked", check_min_temp,self,current_key)
            elif (item['method'] == 'bed_mesh_calibration'):
                item_control_name.connect("clicked", bed_mesh_calibration,self)
            elif (item['method'] == 'start_z_calibration'):
                item_control_name.connect("clicked", start_z_calibration,self)
            elif (item['method'] == 'confrim_calibration'):
                item_control_name.connect("clicked", confrim_calibration,self)
            elif (item['method'] == 'cancle_calibration'):
                item_control_name.connect("clicked", cancle_calibration,self)
            elif (item['method'] == 'cut'):
                item_control_name.connect("clicked", cut,self)
            elif (item['method'] == 'stop_chamber_temperature'):
                item_control_name.connect("clicked", stop_chamber_temperature,self)
            elif (item['method'] == 'clean_nozzle'):
                item_control_name.connect("clicked", clean_nozzle,self)
            elif (item['method'] == 'turn_on_each_detection_bed'):
                item_control_name.connect("clicked", turn_on_each_detection_bed,self)
            elif (item['method'] == 'turn_off_each_detection_bed'):
                item_control_name.connect("clicked", turn_off_each_detection_bed,self)
            elif (item['method'] == 'reload_wifi'):
                item_control_name.connect("clicked", on_refresh_clicked,self)
            elif (item['method'] == 'toolbox' or item['method'] == 'system_settings'):
                item_control_name.connect("clicked", dialog_message,self)


            if current_key.startswith('distance') :
                #Z offset Calibration Bug
                if item_control_name not in self.buttons['distance_button']:
                    self.buttons['distance_button'].append(item_control_name)
            if current_key.startswith('length'):
                self.buttons['length_button'].append(item_control_name)
            if current_key.startswith('speed_consumables') :
                self.buttons['speed_button'].append(item_control_name)
            if current_key.endswith('_mode'):
                self.buttons["print_speed"].append(item_control_name)

            if current_key=='print_busy':
                if  father == 'print_menu':
                    self.is_printing = True
                    item_control_name.set_no_show_all(False)
                else:
                    self.is_printing = False
                    item_control_name.set_no_show_all(True)

            if(self.counter<len(self.items)):
                key_child = list(self.items[self.counter])[0]
                item_child = self.items[self.counter]
                if (item_child[key_child]['type'] == "Grid" and len(key_child.split(" "))>len(key.split(" "))):
                    item_control_name.add(self.create_child_items(self.counter,panel_name,fileinfo,father))

            # if current_key in self.change_item:
            #     self.labels[current_key] = item_control_name
            #     return self.labels[current_key]

            if current_key in self.change_item:
                self.buttons[current_key] = item_control_name
                return self.buttons[current_key]

        elif(item['type'] == "Label"):
            self.counter += 1
            value = ''
            if current_key in {'file_name', 'print_file_name','print_modeling_graphics'} and fileinfo is not None:
                item_control_name = Gtk.Label(hexpand=True, halign=Gtk.Align.START, ellipsize=Pango.EllipsizeMode.END)
                self.filename = fileinfo['filename']
                value=fileinfo['filename'].replace('.gcode', '')
                item_control_name.set_markup(f"<b>{value}</b>")
                return item_control_name
            else:
                value = self._screen.env.from_string(item['value']).render(self.j2_data) if item['value'] else None

            # if (key_array[len(key_array) - 1] in self.change_item):
            #     value=self._printer.get_stat(key_array[len(key_array) - 1], "temperature")

            if(current_key == "percentage_progress"):
                self.percentage_progress=0;
                value=f"{value}%"

            if select_extruder is not None:
                if select_extruder == 'extruder':
                    select_extruder = "T0: "
                else:
                    select_extruder = "T1: "
                if  current_key in ("edit_consumables_title", "control_consumables_title"):
                    value = f"{select_extruder}{value}"

            if (key_array[len(key_array) - 1] == "space_label"):
                item_control_name = Gtk.Label()
                if panel_name == 'air_system':
                    item_control_name.set_vexpand(True)
                else:
                    item_control_name.set_hexpand(True)

            elif (current_key == "file_label"):
                item_control_name = Gtk.Label(label=_(value)+">")
            else:
                item_control_name = Gtk.Label(label=_(value))


            if current_key in self.change_item:
                self.labels[current_key]=item_control_name
                return self.labels[current_key]

        elif(item['type'] == "Grid"):#移除默认边框
            item_control_name = Gtk.Grid(orientation=Gtk.Orientation.HORIZONTAL)
            item_control_name.set_name(current_key)
            width = int(self._screen.env.from_string(item['width']).render(self.j2_data) if item['width'] else None)
            height = int(self._screen.env.from_string(item['height']).render(self.j2_data) if item['height'] else None)

            if(item['column_spacing'] != None):
                column_spacing = int(self._screen.env.from_string(item['column_spacing']).render(self.j2_data) if item['column_spacing'] else None)
                item_control_name.set_column_spacing(50)
            if(item['row_spacing'] != None):
                row_spacing =int(self._screen.env.from_string(item['row_spacing']).render(self.j2_data) if item['row_spacing'] else None)
                item_control_name.set_row_spacing(50)
            if (item['column_homogeneous'] == 'True'):
                item_control_name.set_column_homogeneous(True)
            if (item['row_homogeneous'] == 'True'):
                item_control_name.set_row_homogeneous(True)
            if self._screen.vertical_mode:
                width = int(self._screen.env.from_string(item['v_width']).render(self.j2_data) if item['v_width'] else None)
                height = int(self._screen.env.from_string(item['v_height']).render(self.j2_data) if item['v_height'] else None)
                if (item['v_column_spacing'] != None):
                    v_column_spacing = int(item['v_column_spacing'])
                    item_control_name.set_column_spacing(v_column_spacing)
                if (item['v_row_spacing'] != None):
                    v_row_spacing = int(item['v_row_spacing'])
                    item_control_name.set_row_spacing(v_row_spacing)

            item_control_name.set_size_request(width, height)
            i+=1
            if (key_array[len(key_array) - 1] == "file_list_body_grid"):
                self.labels['flowbox']= item_control_name
                self.counter=i
                return self.labels['flowbox']
            if (current_key == "wifi_message_grid"):
                self.grid[current_key]= item_control_name
                self.counter=i
                return self.grid[current_key]


            while i<len(self.items):
                key_child = list(self.items[i])[0]
                key_father = ' '.join(key_child.split()[:-1]) if key_child and key_child.strip() else ''
                item_child = self.items[i][key_child]
                if (key_father == key and len((list(self.items[i])[0]).split()) > 1):
                    if self._screen.vertical_mode:
                        item_control_name.attach(self.create_child_items(i,panel_name,fileinfo,father,select_extruder),
                                                   int(item_child['v_column']),
                                                   int(item_child['v_row']),
                                                   int(item_child['v_columnspan']),
                                                   int(item_child['v_rowspan']))
                    else:
                        item_control_name.attach(self.create_child_items(i, panel_name, fileinfo, father, select_extruder),
                                                    int(item_child['column']),
                                                    int(item_child['row']),
                                                    int(item_child['columnspan']),
                                                    int(item_child['rowspan']))
                    i = self.counter
                else:
                    i = self.counter + 1
                    break

        elif (item['type'] == "Switch"):
            self.counter += 1
            item_control_name= Gtk.Switch()
            value = self._screen.env.from_string(item['value']).render(self.j2_data) if item['value'] else None
            # width = int(self._screen.env.from_string(item['width']).render(self.j2_data) if item['width'] else None)
            # height = int(self._screen.env.from_string(item['height']).render(self.j2_data) if item['height'] else None)
            # item_control_name.set_size_request(120, 60)
            if current_key == "light_switch":
                item_control_name.set_active(True)  # 强制开启
                # item_control_name.set_sensitive(False)  # 禁止点击
                return item_control_name
            if current_key == "wifi_switch":
                item_control_name.connect("notify::active", on_wifi_switch_toggled, self)
                self.switch[current_key] = item_control_name
                return self.switch[current_key]

        elif (item['type'] == "ProgressBar"):
            self.counter += 1
            item_control_name= Gtk.ProgressBar()
            #设置进度条百分比
            # item_control_name.set_fraction(self.percentage_progress)
            item_control_name.set_fraction(0)
            item_control_name.set_show_text(False)
            width = int(self._screen.env.from_string(item['width']).render(self.j2_data) if item['width'] else None)
            height = int(self._screen.env.from_string(item['height']).render(self.j2_data) if item['height'] else None)
            if self._screen.vertical_mode:
                width = int(self._screen.env.from_string(item['v_width']).render(self.j2_data) if item['v_width'] else None)
                height = int(self._screen.env.from_string(item['v_height']).render(self.j2_data) if item['v_height'] else None)
                if current_key == 'h_progress_bar':
                    item_control_name.set_no_show_all(True)
            elif current_key == 'v_progress_bar':
                    item_control_name.set_no_show_all(True)
            item_control_name.set_name("rotated-progressbar")
            item_control_name.set_size_request(width, height)
            self.labels[current_key]=item_control_name

        elif (item['type'] == "RadioButton"):
            self.counter += 1
            value = self._screen.env.from_string(item['value']).render(self.j2_data) if item['value'] else None
            if(not self.create_radionButton):
                self.radioButton['radio_button_group'] =  Gtk.RadioButton.new_with_label_from_widget(None, value)
                item_control_name = self.radioButton['radio_button_group']
                self.create_radionButton = True
            else:
                item_control_name = Gtk.RadioButton.new_with_label_from_widget(self.radioButton['radio_button_group'], value)
                # self.radioButton[key].connect("toggled", self.on_radio_toggled, value)
                # 创建单选按钮组（普通样式，无圆形图标）
                # self.radioButton[key].set_mode(False)

        elif (item['type'] == "Entry"):
            self.counter += 1
            value = self._screen.env.from_string(item['value']).render(self.j2_data) if item['value'] else None
            item_control_name = Gtk.Entry()
            item_control_name.set_text("℃")  # 初始带单位
            item_control_name.set_position(0)  # 光标在最前
            item_control_name.set_alignment(0.5) # 文本居中
            if self._screen.vertical_mode:
                item_control_name.set_size_request(400,80)
            else:
                item_control_name.set_size_request(400,100)
            item_control_name.get_style_context().add_class("entry_temperature")
            # panel_name extruder_temperature chassis_temperature heater_bed_temperature
            self.entry[panel_name] = item_control_name

        elif (item['type'] == "ComboBoxText"):
            self.counter += 1
            item_control_name = Gtk.ComboBoxText()
            combobox_key=current_key
            combobox_items=STATIC_CONSUMABLES[combobox_key]
            for combobox_item in combobox_items:
                item_control_name.append_text(combobox_item)
            item_control_name.set_active(0)
            width = int(self._screen.env.from_string(item['width']).render(self.j2_data) if item['width'] else None)
            height = int(self._screen.env.from_string(item['height']).render(self.j2_data) if item['height'] else None)
            if self._screen.vertical_mode:
                width = int(self._screen.env.from_string(item['v_width']).render(self.j2_data) if item['v_width'] else None)
                height = int(self._screen.env.from_string(item['v_height']).render(self.j2_data) if item['v_height'] else None)
            item_control_name.set_size_request(width, height)
            style = self._screen.env.from_string(item['style']).render(self.j2_data) if item['style'] else None
            item_control_name.get_style_context().add_class(style)



        elif (item['type'] == "TextView"):
            self.counter += 1
            value = self._screen.env.from_string(item['value']).render(self.j2_data) if item['value'] else None
            item_control_name = Gtk.TextView()
            item_control_name.set_editable(False)# 设为只读
            item_control_name.set_cursor_visible(False)  # 隐藏光标（可选）
            buffer = item_control_name.get_buffer()
            buffer.set_text(value)

        elif (item['type'] == "CheckButton"):
            self.counter += 1
            value = self._screen.env.from_string(item['value']).render(self.j2_data) if item['value'] else None
            item_control_name = Gtk.CheckButton(label=_(value))
            item_control_name.set_active(True)  # 设为选中

        elif (item['type'] == "ColorButton"):
            self.counter += 1
            item_control_name = Gtk.ColorButton()
            value = self._screen.env.from_string(item['value']).render(self.j2_data) if item['value'] else None
            rgba = Gdk.RGBA()
            rgba.parse(value)  # 可以是 "blue", "#ff0000", "rgb(255,0,0)" 等
            item_control_name.set_rgba(rgba)
            width = int(self._screen.env.from_string(item['width']).render(self.j2_data) if item['width'] else None)
            height = int(self._screen.env.from_string(item['height']).render(self.j2_data) if item['height'] else None)
            if self._screen.vertical_mode:
                width = int(
                    self._screen.env.from_string(item['v_width']).render(self.j2_data) if item['v_width'] else None)
                height = int(
                    self._screen.env.from_string(item['v_height']).render(self.j2_data) if item['v_height'] else None)
            item_control_name.set_size_request(width, height)
            item_control_name.connect("color-set", self.on_color_chosen)

        return item_control_name


    def evaluate_enable(self, enable):
        """
            是否启用按钮
        :param enable:
        :return:
        """
        if enable == "{{ moonraker_connected }}":
            logging.info(f"moonraker connected {self._screen._ws.connected}")
            return self._screen._ws.connected
        try:
            j2_temp = Template(enable, autoescape=True)
            return j2_temp.render(self.j2_data) == 'True'
        except Exception as e:
            logging.debug(f"Error evaluating enable statement: {enable}\n{e}")
            return False

    def process_update(self, panel_name,action,data):
        if self.file_metadata is None and self.filename is not None:
            self.init_file_data(True)
        if panel_name in ( "home_menu", "printer_control_menu", "air_system"):
            for dev in self.labels:
                for type in ('extruder', 'extruder1','heater_bed','chassis'):
                    if dev.endswith(f'{type}_temperature'):
                        if type == "chassis":
                            type = "temperature_sensor filament_box_temp"
                        self.update_temp(
                            panel_name,
                            type,
                            self._printer.get_stat(type, "temperature"),
                            self._printer.get_stat(type, "target"),
                            self._printer.get_stat(type, "power"),
                            name=dev
                        )
                        break
            if panel_name in ("printer_control_menu", "air_system"):
                # 'fan':{'rpm': None, 'speed': 1.0}
                value = ''
                if 'fan' in data and 'speed' in data['fan']:
                    if data['fan']['speed'] > 0:
                        value = 'On'
                    else:
                        value = 'Off'
                    if panel_name == "printer_control_menu":
                        self.labels['fen_model'].set_text(f"{_('Fan : ')}{_(value)}")
                    else:
                        self.labels['fen_model'].set_text(f'{_(value)}')
        if panel_name == "printer_control_menu" :
            update_print_speed_message(self, data)
        if panel_name == "speed_control":
            update_speed_button(self, data)

        #更新打印信息
        if panel_name == "print_menu" and action == 'notify_status_update' :
            update_time_left(self,action,data)

        # if panel_name == "wifi":
        #     reload_wifi(None, self)

        #更新Z偏移校准信息
        elif panel_name == "z_offset_calibration":
            if action == "notify_status_update":
                if self._printer.get_stat("toolhead", "homed_axes") != "xyz":
                    self.labels['z_value'].set_text("Z: ?")
                elif "gcode_move" in data and "gcode_position" in data['gcode_move']:
                    update_position(self, data['gcode_move']['gcode_position'])
                if "manual_probe" in data:
                    if data["manual_probe"]["is_active"]:
                        buttons_calibrating(self)
                    else:
                        buttons_not_calibrating(self)
        #  删除文件后刷新页面
        elif "action" in data and data["action"] == "delete_file":
            refresh_loading(None,self)

    #打印文件列表页面，加载文件列表方法
    def load_files(self, result,method, params):
        set_loading(self,True)
        items = [create_print_file_list_item(self,item) for item in
                 [*result["result"]["dirs"], *result["result"]["files"]]]
        i = column = row = 0
        for item in filter(None, items):
            self.labels['flowbox'].attach(item, column, row, 1, 1)
            i += 1
            if self._screen.vertical_mode:
                if i % 2 == 0:
                    row += 1
                    column = 0
                else:
                    column += 1
            else:
                if i % 4 == 0:
                    row += 1
                    column = 0
                else:
                    column += 1
        set_loading(self,False)

    #请求文件详细信息
    def init_file_data(self, is_init):
        if is_init:
            self._screen._ws.klippy.get_file_metadata(self.filename, self._callback)
        return True

    #回滚 加载打印文件信息
    def _callback(self, result, method, params):
        self.file = {}
        self.file_metadata = {}
        self.gcodes_path = None
        if "error" in result:
            logging.debug(result["error"])
            return
        if method == "server.files.metadata":
            for x in result['result']:
                self.file_metadata[x] = result['result'][x]

        file_time = filament_time = None
        progress = (
                max(self._printer.get_stat('virtual_sdcard', 'file_position') - self.file_metadata['gcode_start_byte'],
                    0)
                / (self.file_metadata['gcode_end_byte'] - self.file_metadata['gcode_start_byte'])
        ) if "gcode_start_byte" in self.file_metadata else self._printer.get_stat('virtual_sdcard', 'progress')

        last_time = self.file_metadata['last_time'] if "last_time" in self.file_metadata else 0
        slicer_time = self.file_metadata['estimated_time'] if 'estimated_time' in self.file_metadata else 0
        print_duration = float(self._printer.get_stat('print_stats', 'print_duration'))
        if print_duration < 1:  # No-extrusion
            if last_time:
                print_duration = last_time * progress
            elif slicer_time:
                print_duration = slicer_time * progress
            else:
                print_duration = float(self._printer.get_stat('print_stats', 'total_duration'))

        fila_used = float(self._printer.get_stat('print_stats', 'filament_used'))
        if 'filament_total' in self.file_metadata and self.file_metadata['filament_total'] >= fila_used > 0:
            filament_time = (print_duration / (fila_used / self.file_metadata['filament_total']))
            # self.labels["filament_time"].set_label(self.format_time(filament_time))
        else:
            filament_time = 0
        if progress > 0:
            file_time = (print_duration / progress)
            # self.labels["file_time"].set_label(self.format_time(file_time))
        else:
            file_time = 0

        estimated = 0
        timeleft_type = self._config.get_config()['main'].get('print_estimate_method', 'auto')
        if timeleft_type == "file":
            estimated = file_time
        elif timeleft_type == "filament":
            estimated = filament_time
        elif timeleft_type == "slicer":
            estimated = slicer_time
        else:
            estimated = self.estimate_time(
                progress, print_duration, file_time, filament_time, slicer_time, last_time
            )
        if estimated > 1:
            progress = min(max(print_duration / estimated, 0), 1)
            #初始化剩余打印时长  print_duration 打印持续时间
            time = print_time_format(estimated)
            self.labels["remaining_time"].set_label(time)


        # 更新进度条
        if progress is not None:
            self.labels["percentage_progress"].set_label(f' {int(progress * 100)}%')
            self.labels['v_progress_bar'].set_fraction(progress)
            self.labels['h_progress_bar'].set_fraction(progress)

        # if ('toolhead' in data) and ('estimated_print_time' in data['toolhead']):
        #     estimated_print_time = int(data['toolhead']['estimated_print_time'])
        # #  打印层数
        # self.labels['total_layers'].set_label(f"{data['print_stats']['info']['total_layer']}")
        # self.labels['current_layers'].set_label()


