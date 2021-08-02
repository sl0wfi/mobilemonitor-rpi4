#!/usr/bin/env python3

#This file written by sl0wfi
#Many thanks to notaco as large chunks of this are from https://github.com/notaco/kismet_status_leds.py

#Setup on kali as of July 2020
#sudo apt-get install python3-pip
#sudo pip3 install adafruit-circuitpython-ssd1306
#pip3 install adafruit-blinka
#sudo apt-get install python3-pil
#sudo pip3 install psutil
#sudo pip3 install requests
#sudo pip3 install gpiozero

# Import libraries

# import for modules that are standard to python3
import argparse, os, sys, json, traceback, time, asyncio, threading, subprocess
from queue import Queue

# import websocket-client
try:
    import websocket
except:
    print("Failed to load websocket python3 module. Install using 'pip3 install websocket-client'")
    sys.exit(1)

# configuration class
class configuration(object):
    def __init__(self):
            # set up and run argument parser
            self.parser = argparse.ArgumentParser(description="{}, a mobile wireless monitoring platform".format(sys.argv[0]))
            self.parser.add_argument('-c',"--config", action="store", dest="config_file",
                                            default="config.json", help="json config file, default config.json")
            self.parser.add_argument('-k','--kismet-host', action="store", dest="host", help="remote Kismet server on host:port")
            self.parser.add_argument('-u',"--user", action="store", dest="user", help="Kismet username for websocket eventbus")
            self.parser.add_argument('-p',"--password", action="store", dest="password", help="Kismet password for websocket eventbus")
            self.parser.add_argument("--uri-prefix", action="store", dest="uri_prefix", help="Kismet httpd uri prefix")
            self.parser.add_argument("--disable-reconnect", action="store_true", dest="no_reconnect", help="disable websocket reconnect")
            self.parser.add_argument("--reconnect-delay", action="store", type=int, dest="reconnect_delay", help="websocket reconnect delay (seconds)")
            self.parser.add_argument("--disable-lpm", action="store_true", dest="no_lpm", help="disable all local process management")
            self.parser.add_argument("--disable-gpio", action="store_true", dest="no_gpio", help="disable all gpio usage")
            self.parser.add_argument("--disable-gpio-buttons", action="store_true", dest="no_buttons", help="disable gpio button usage")
            self.parser.add_argument("--disable-gpio-leds", action="store_true", dest="no_leds", help="disable gpio led usage")
            self.parser.add_argument("--disable-i2c-display", action="store_true", dest="no_i2c", help="disable i2c display")
            self.parser.add_argument("--disable-stdout-msg", action="store_true", dest="no_stdout", help="disable writing messages to stdout")
            self.parser.add_argument("--debug", action="store_true", dest="debug", help="enable debug messages")
            self.parser.add_argument("--debug-ws", action="store_true", dest="debug_ws", help="enable websocket debug messages")
            cmd_args = self.parser.parse_args()

            # read configuration file
            self.config_file = cmd_args.config_file
            if not os.path.isfile(os.path.expanduser(self.config_file)):
                print("configuration file {} not found!".format(self.config_file))
                sys.exit(1)
            elif not os.access(os.path.expanduser(self.config_file), os.R_OK):
                print("configuration file {} not readable!".format(self.config_file))
                sys.exit(1)
            try:
                with open(os.path.expanduser(self.config_file), "r") as json_file:
                    conf_data = json.load(json_file)
            except Exception as err:
                print(err)
                print("Error parsing json config file {}".format(self.config_file))
                sys.exit(1)

            # check for debugging
            if cmd_args.debug or conf_data['debug'] == True:
                self.debug = True
            else:
                self.debug = False

            # dump configs for debug
            if self.debug:
                print("DEBUG config init: conf_data from {}".format(self.config_file))
                print(json.dumps(conf_data, indent=4, sort_keys=True))
                print("DEBUG config init: cmd_args from argparse (taking precedence)")
                print(cmd_args)

            # ensure there is a user and password
            if cmd_args.user != None:
                self.username = cmd_args.user
            else:
                try: self.username = conf_data['kismet_httpd']['username']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("ERROR: Failed to find configuration for kismet httpd username!")
                    sys.exit(1)

            if cmd_args.password != None:
                self.password = cmd_args.password
            else:
                try: self.password = conf_data['kismet_httpd']['password']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("ERROR: Failed to find configuration for kismet httpd password!")
                    sys.exit(1)

            # check the rest of arguments and config file, warn and default as needed
            if cmd_args.host != None:
                eq = cmd_args.host.find(":")
                if eq == -1:
                    print("ERROR: bad kismet host argument, expected host:port for websocket connection.")
                    sys.exit(1)

                self.address = cmd_args.host[:eq]
                self.port = int(cmd_args.host[eq+1:])
            else:
                try: self.address = conf_data['kismet_httpd']['address']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("Unable to find configuration for kismet httpd server address!")
                    print("Setting to 'localhost'")
                    self.address = 'localhost'
                try: self.port = conf_data['kismet_httpd']['port']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("Unable to find configuration for kismet httpd server port!")
                    print("Setting to 2501")
                    self.port = '2501'

            if cmd_args.uri_prefix != None:
                self.uri_prefix = cmd_args.uri_prefix
            else:
                try: self.uri_prefix = conf_data['kismet_httpd']['uri_prefix']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("Unable to find configuration for kismet httpd uri prefix!")
                    print("Setting to ''")
                    self.uri_prefix = ''

            if cmd_args.no_reconnect:
                self.enable_reconnect = False
            else:
                try: self.reconnect = conf_data['kismet_httpd']['reconnect']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("Unable to find configuration for kismet httpd reconnect!")
                    print("Setting to True")
                    self.reconnect = True

            if cmd_args.reconnect_delay != None:
                self.reconnect_delay = cmd_args.reconnect_delay
            else:
                try: self.reconnect_delay = conf_data['kismet_httpd']['reconnect_delay']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("Unable to find configuration for kismet httpd reconnect delay!")
                    print("Setting to 3")
                    self.reconnect_delay = 3

            if cmd_args.no_lpm:
                self.local_process_management = { "enabled": False }
            else:
                try: self.local_process_management = conf_data['local_process_management']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("Unable to find configuration for local process management!")
                    print("Disabling.")
                    self.local_process_management = { "enabled": False }

            if cmd_args.no_gpio:
                self.local_gpio = { "enabled": False }
            else:
                try: self.local_gpio = conf_data['local_gpio']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("Unable to find configuration for local gpio!")
                    print("Disabling.")
                    self.local_gpio = { "enabled": False }

            if cmd_args.no_buttons:
                self.local_gpio['input_buttons'] = []

            if cmd_args.no_leds:
                self.local_gpio['leds'] = []

            if cmd_args.no_i2c:
                self.i2c_display = { "enabled": False }
            else:
                try: self.i2c_display = conf_data['i2c_display']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("Unable to find configuration for i2c_display!")
                    print("Disabling.")
                    self.i2c_display = { "enabled": False }

            if cmd_args.no_stdout:
                self.data_to_stdout = False
            else:
                try: self.data_to_stdout = conf_data['msg_to_stdout']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("Unable to find configuration for msg_to_stdout!")
                    print("Enabling.")
                    self.data_to_stdout = True

            if cmd_args.debug_ws:
                self.debug_ws = True
            else:
                try: self.debug_ws = conf_data['debug_ws']
                except Exception as err:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                    print("Unable to find configuration for debug_ws!")
                    print("Disabling.")
                    self.data_to_stdout = False

# class for event defs and control
class event_control(object):
    def __init__(self):
        self.ws_event = { 'ws_connected': [],
                          'gps_status': [],
                          'new_ssid': [],
                          'new_ap': [],
                          'new_device': [] }

    def wsc_new(self, event):
        if config.debug: print("Websocket event: " + str(event))
        for cb in self.ws_event[event['type']]:
            eventloop.call_soon(cb, event, False)

# class for handling the websocket connection
class ws_connector(object):
    # init the variables for the class
    def __init__(self, addr, port, un, pw, **kwargs):
        self.kismet_address = addr
        self.kismet_port = port
        self.kismet_user = un
        self.kismet_pass = pw

        if 'reconnect' in kwargs.keys():
            self.reconnect = kwargs['reconnect']
        else:
            self.reconnect = True
        if 'reconnect_delay' in kwargs.keys():
            self.reconnect_delay = kwargs['reconnect_delay']
        else:
            self.reconnect_delay = 3
        if 'debug' in kwargs.keys():
            self.debug = kwargs['debug']
        else:
            self.debug = False

        # create thread safe queue
        self.msgs = Queue()

        # rest of variables are only read from main thread
        self.reset_status(True)

    # method to setup variables at init or new ws connection
    def reset_status(self, init=False):
        self.timestamp = -1
        self.gps_fix = "Unknown"
        if init is True:
            self.error_state = 1
            self.error_msg = "Not connected yet!"

    # parse eventbus timestamp
    def parse_ts(self, msg_dict):
        self.timestamp = msg_dict['TIMESTAMP']['kismet.system.timestamp.sec']

    # parse eventbus message to create message for io display
    def parse_msg(self, msg_dict):
        msg_str = msg_dict['MESSAGE']['kismet.messagebus.message_string']

        io_msg = None
        io_ev = None
        if "SSID" in msg_str:
            io_msg = "Found new SSID"
            io_ev = "new_ssid"
        if "new 802.11 Wi-Fi access point" in msg_str:
            io_msg = "Found new access point"
            io_ev = "new_ap"
        if "new 802.11 Wi-Fi device" in msg_str:
            io_msg = "Found new device"
            io_ev = "new_device"
        # see if we have a message for io, put on queue
        if not io_msg is None:
            self.msgs.put({'text': io_msg, 'ts': self.timestamp})
            eventloop.call_soon_threadsafe(events.wsc_new, {'type': io_ev, 'ts': self.timestamp})

    # parse eventbus message to create message for io display
    def parse_gps(self, msg_dict):
        gps_msg = msg_dict['GPS_LOCATION']['kismet.common.location.fix']
        if gps_msg == 3:
            if self.gps_fix != "3D fix":
                self.gps_fix = "3D fix"
                eventloop.call_soon_threadsafe(events.wsc_new, {'type': 'gps_status', 'state': 2})
        elif gps_msg == 2:
            if self.gps_fix != "2D fix":
                self.gps_fix = "2D fix"
                eventloop.call_soon_threadsafe(events.wsc_new, {'type': 'gps_status', 'state': 1})
        else:
            if self.gps_fix != "NO LOCK":
                self.gps_fix = "NO LOCK"
                eventloop.call_soon_threadsafe(events.wsc_new, {'type': 'gps_status', 'state': 0})

    # ws client callback for new messages
    def on_message(self, ws, message):
        deser_msg = json.loads(message)
        for key in deser_msg.keys():
            if key == "TIMESTAMP":
                self.parse_ts(deser_msg)
            if key == "MESSAGE":
                self.parse_msg(deser_msg)
            if key == "GPS_LOCATION":
                self.parse_gps(deser_msg)

    # ws client callback for error
    def on_error(self, ws, error):
        self.reset_status()
        # signal error state and provide an error message
        print(error)
        self.error_state = 1
        self.error_msg = type(error).__name__

    # ws client callback for closed connection
    def on_close(self, ws, close_status_code, close_msg):
        print("Websocket connection closed.")
        # reset status variables
        self.reset_status()
        # signal error state and provide a hopeful error message
        self.error_state = 1
        self.error_msg = "Connection closed, will retry in {} seconds".format(self.reconnect_delay)

    # ws client callback for opened connection
    def on_open(self, ws):
        print("Connected to websocket, subscribing")
        # clear error state and error message
        self.error_state = 0
        self.error_msg = ''
        # put connect message on queue
        self.msgs.put({'text': "Connected to kismet at {}".format(self.kismet_address), 'ts': self.timestamp})
        # send eventbus subscribes
        time.sleep(1)
        ws.send(json.dumps({"SUBSCRIBE":"MESSAGE"}))
        time.sleep(1)
        ws.send(json.dumps({"SUBSCRIBE":"TIMESTAMP"}))
        time.sleep(1)
        ws.send(json.dumps({"SUBSCRIBE":"GPS_LOCATION"}))
        eventloop.call_soon_threadsafe(events.wsc_new, {'type': 'ws_connected', 'state': 2})

    # method to run ws client
    def ws_run(self):
        eventloop.call_soon_threadsafe(events.wsc_new, {'type': 'ws_connected', 'state': 0})
        print("Starting websocket connection")
        self.ws = websocket.WebSocketApp("ws://{}:{}/eventbus/events.ws?user={}&password={}".format(self.kismet_address,self.kismet_port,self.kismet_user,self.kismet_pass),
                                on_open= lambda ws: self.on_open(self.ws),
                                on_message= lambda ws,msg: self.on_message(self.ws, msg),
                                on_error= lambda ws,msg: self.on_error(self.ws, msg),
                                on_close= lambda ws: self.on_close(self.ws, self.close_status_code, self.close_msg))
        # use infinite loop to restart (avoids stack overflow from recursion in on_close cb)
        while True:
            self.ws.run_forever()
            eventloop.call_soon_threadsafe(events.wsc_new, {'type': 'ws_connected', 'state': 0})
            eventloop.call_soon_threadsafe(events.wsc_new, {'type': 'gps_status', 'state': 0})
            if self.reconnect:
                time.sleep(self.reconnect_delay)
                if config.debug: print("Reconnect loop")
            else:
                break

# class for gpio io_controller
class gpio_controller(object):
    def __init__(self):
        print("Configuring local gpio.")
        self.button_lines = {'show_stats': None}
        self.buttons = {}

        self.led_lines = {}
        self.leds = {}

        self.np_pixels = {}
        self.np_running = False

    def configure_buttons(self, btns):
        try:
            for btn in btns['lines']:
                try:
                    if btn['function'] == 'show_stats':
                        self.button_lines['show_stats'] = btn['gpio_pin']
                except Exception as err:
                    if config.debug:
                        traceback.print_tb(err.__traceback__)
                        print(err)
                    print("Failed to configure 'lines' entry in 'input_buttons':")
                    print(btn)
        except Exception as err:
            if config.debug:
                traceback.print_tb(err.__traceback__)
                print(err)
            print("Failed to configure 'lines' in 'input_buttons'")

    def configure_leds(self, leds, events):
        ws_evt = events.ws_event
        try:
            if 'duration' in leds.keys():
                self.led_duration = leds['duration']
            else:
                self.led_duration = 0.3
                print(f"In configuration 'leds' is enabled but 'duration' is not defined. Defaulting to '{self.led_duration}'")
            for led in leds['lines']:
                pin = led['gpio_pin']
                try:
                    for ev in ws_evt.keys():
                        if led['function'] == ev:
                            self.led_lines[ev] = { 'pin': pin, 'state': 0 }
                            ws_evt[ev].append(self.led_change)
                            if not pin in self.leds.keys():
                                self.leds[pin] = LED(pin)
                except Exception as err:
                    if config.debug:
                        traceback.print_tb(err.__traceback__)
                        print(err)
                    print("Failed to configure 'lines' entry in 'leds':")
                    print(led)
        except Exception as err:
            if config.debug:
                traceback.print_tb(err.__traceback__)
                print(err)
            print("Failed to configure 'lines' in 'leds'")

    def led_change(self, event, timed=False, set_on=True):
        ev = event['type']
        pin = self.led_lines[ev]['pin']
        if config.debug: print("led_change: "+ev+" "+str(self.led_lines[ev]))

        # handled stated events, 0 for off, 1 for flashing, 2, for on
        if 'state' in event.keys():
            # off/on being simple
            if event['state'] == 0:
                self.leds[pin].off()
                self.led_lines[ev]['state'] = 0
            elif event['state'] == 2:
                self.leds[pin].on()
                self.led_lines[ev]['state'] = 2
            # flashing, timed callbacks with args to indicate where we are
            elif event['state'] == 1:
                # check for and localize the state, saves on ifs later
                if 'state' in self.led_lines[ev].keys():
                    pstate = self.led_lines[ev]['state']
                else:
                    pstate = 0
                # new trigger coming from wsc
                if not timed and pstate != 1:
                    if pstate == 0:
                        self.leds[pin].on()
                    else:
                        self.leds[pin].ff()
                    self.led_lines[ev]['state'] = 1
                    eventloop.call_later(self.led_duration, self.led_change, event, True, True)
                # now just the timed callbacks
                elif timed and pstate == 1:
                    if set_on:
                        self.leds[pin].on()
                        eventloop.call_later(self.led_duration, self.led_change, event, True, False)
                    if not set_on:
                        self.leds[pin].off()
                        eventloop.call_later(self.led_duration, self.led_change, event, True, True)
                # handle some wtf's
                elif timed and config.debug: print("led_change: 'timed' call with unexpected state: {}".format(event))
            elif config.debug: print("led_change: Unexpected 'state' passed: {}".format(event['state']))
        # now for events with a timestamp
        elif 'ts' in event.keys():
            if not timed:
                if not 'ts' in self.led_lines[ev].keys() or event['ts'] > self.led_lines[ev]['ts']:
                    self.led_lines[ev]['ts'] = event['ts']
                    self.leds[pin].on()
                    eventloop.call_later(self.led_duration, self.led_change, event, True, False)
            else:
                if self.led_lines[ev]['ts'] == event['ts']:
                    self.leds[pin].off()
        # and error for unhandled
        elif config.debug: print("led_change: Unexpected 'event' passed: {}".format(event))

    def configure_neopixel(self, neopixels, events):
        ws_evt = events.ws_event
        try:
            np_pin = getattr(board, 'D'+str(neopixels['pin']))
            if 'duration' in neopixels.keys():
                self.np_duration = neopixels['duration']
            else:
                self.np_duration = 0.3
                print(f"In configuration 'neopixels' is enabled but 'duration' is not defined. Defaulting to '{self.np_duration}'")
            if 'count' in neopixels.keys():
                cnt = neopixels['count']
            else:
                cnt = len(neopixels['pixels'])
                print(f"In configuration 'neopixels' is enabled but 'count' is not defined. Using 'pixels' length: {cnt}")
            if 'brightness' in neopixels.keys():
                bright = neopixels['brightness']
            else:
                bright = 0.2
                print(f"In configuration 'neopixels' is enabled but 'order' is not defined. Defaulting to '{bright}'")
            if 'order' in neopixels.keys():
                order = neopixels['order']
            else:
                if len(neopixels['pixels'][0]['color']) == 3:
                    order = "GRB"
                elif len(neopixels['pixels'][0]['color']) == 4:
                    order = "GRBW"
                else:
                    raise Exception("Unexpected length of 'color' for first element in 'pixels', 3 or 4 bytes expected!")
                print(f"In configuration 'neopixels' is enabled but 'order' is not defined. Defaulting to '{order}'")
            self.pixels = neopixel.NeoPixel(np_pin, cnt, brightness=bright, pixel_order=order, auto_write=True)
            try:
                for i in range(len(neopixels['pixels'])):
                    try:
                        for ev in ws_evt.keys():
                            if neopixels['pixels'][i]['function'] == ev:
                                self.np_pixels[ev] = { 'place': i,
                                                       'color': neopixels['pixels'][i]['color'] }
                                # writing to the pixels mainly to ensure permissions
                                self.pixels[i] = neopixels['pixels'][i]['color']
                                time.sleep(.1)
                                self.pixels[i] = [0] * len(neopixels['pixels'][i]['color'])
                                ws_evt[ev].append(self.np_change)
                    except Exception as err:
                        if config.debug:
                            traceback.print_tb(err.__traceback__)
                            print(err)
                        print("Failed to configure 'pixels' entry in 'neopixels':")
                        print(np)
            except Exception as err:
                if config.debug:
                    traceback.print_tb(err.__traceback__)
                    print(err)
                print("Failed to configure 'pixels' in 'neopixels'")

            self.np_running = True
        except Exception as err:
            if config.debug:
                traceback.print_tb(err.__traceback__)
            print(err)
            print("Failed to configure neopixels!")

    def np_change(self, event, timed=False, set_color=True):
        # localize some awkwardness for readablity
        ev = event['type']
        place = self.np_pixels[ev]['place']
        color = self.np_pixels[ev]['color']
        black = [0]*len(self.np_pixels[ev]['color'])
        # debug msg
        if config.debug: print("np_change: "+ev+" "+str(self.np_pixels[ev]))

        # handled stated events, 0 for off, 1 for flashing, 2, for on
        if 'state' in event.keys():
            # off/on being simple
            if event['state'] == 0:
                self.pixels[place] = black
                self.np_pixels[ev]['state'] = 0
            elif event['state'] == 2:
                self.pixels[place] = color
                self.np_pixels[ev]['state'] = 2
            # flashing, timed callbacks with args to indicate where we are
            elif event['state'] == 1:
                # check for and localize the state, saves on ifs later
                if 'state' in self.np_pixels[ev].keys():
                    pstate = self.np_pixels[ev]['state']
                else:
                    pstate = 0
                # new trigger coming from wsc
                if not timed and pstate != 1:
                    if pstate == 0:
                        self.pixels[place] = color
                    else:
                        self.pixels[place] = black
                    self.np_pixels[ev]['state'] = 1
                    eventloop.call_later(self.np_duration, self.np_change, event, True, True)
                # now just the timed callbacks
                elif timed and pstate == 1:
                    if set_color:
                        self.pixels[place] = color
                        eventloop.call_later(self.np_duration, self.np_change, event, True, False)
                    if not set_color:
                        self.pixels[place] = black
                        eventloop.call_later(self.np_duration, self.np_change, event, True, True)
                # handle some wtf's
                elif timed and config.debug: print("np_change: 'timed' call with unexpected state: {}".format(event))
            elif config.debug: print("np_change: Unexpected 'state' passed: {}".format(event['state']))
        # now for events with a timestamp
        elif 'ts' in event.keys():
            if not timed:
                if not 'ts' in self.np_pixels[ev].keys() or event['ts'] > self.np_pixels[ev]['ts']:
                    self.np_pixels[ev]['ts'] = event['ts']
                    self.pixels[place] = color
                    eventloop.call_later(self.np_duration, self.np_change, event, True, False)
            else:
                if self.np_pixels[ev]['ts'] == event['ts']:
                    self.pixels[place] = black
        # and error for unhandled
        elif config.debug: print("np_change: Unexpected 'event' passed: {}".format(event))

    def button_watcher(self, gpio_line, cb):
        self.buttons['line_'+str(gpio_line)] = Button(gpio_line)
        self.buttons['line_'+str(gpio_line)].when_pressed = cb

# class for display drawing and updating
class i2c_controller(object):
    def __init__(self, width, height):
        # Create the I2C interface.
        self.i2c = busio.I2C(SCL, SDA)

        # no other drivers yet so use ssd1306
        # Create the SSD1306 OLED class
        self.disp = adafruit_ssd1306.SSD1306_I2C(width, height, self.i2c)

        # Clear display.
        self.disp.fill(0)
        self.disp.show()

        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        self.width = self.disp.width
        self.height = self.disp.height
        self.image = Image.new("1", (self.width, self.height))

        # Get drawing object to draw on image.
        self.draw = ImageDraw.Draw(self.image)

        # Draw a black filled box to clear the image.
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        self.padding = -2
        self.top = self.padding
        self.bottom = self.height - self.padding
        # Move left to right keeping track of the current x position for drawing shapes.
        self.x = 0

        # Load default font.
        self.font = ImageFont.load_default()

    def draw_screen(self, timestamp, gps_fix):
        # Draw a black filled box to clear the image.
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

        # Shell scripts for system monitoring from here:
        # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
        #self.cmd = "hostname -I | cut -d' ' -f1"
        #self.IP = subprocess.check_output(self.cmd, shell=True).decode("utf-8")
        #self.cmd = 'cut -f 1 -d " " /proc/loadavg'
        #self.CPU = subprocess.check_output(self.cmd, shell=True).decode("utf-8")
        self.cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'"
        self.MemUsage = subprocess.check_output(self.cmd, shell=True).decode("utf-8")
        self.cmd = 'df -h | awk \'$NF=="/"{printf "Disk: %d/%d GB  %s", $3,$2,$5}\''
        self.Disk = subprocess.check_output(self.cmd, shell=True).decode("utf-8")

        # Write four lines of text.
        self.draw.text((self.x, self.top + 0), "GPS: " + gps_fix, font=self.font, fill=255)
        self.draw.text((self.x, self.top + 8), "TS: " + str(timestamp), font=self.font, fill=255)
        self.draw.text((self.x, self.top + 16), self.MemUsage, font=self.font, fill=255)
        self.draw.text((self.x, self.top + 25), self.Disk, font=self.font, fill=255)

        # Display image.
        self.disp.image(self.image)
        self.disp.show()
        #time.sleep(self.DISPLAY_ON)
        #self.disp.fill(0)
        #self.disp.show()
        #time.sleep(self.DISPLAY_OFF)

# class for io loop
class io_controller(object):
    # init with configuration
    def __init__(self, ws_connector, gpio=None, disp=None, show_stdout=True,
                    screen_update_delay=3, msg_screen_time=1, msg_timeout=10):
        # reference to ws_connector instance to read status from
        self.wsc = ws_connector
        # reference to gpio_controller
        self.gpio_con = gpio
        # reference to i2c_display instance to output data
        self.i2c_disp = disp
        # setting for prints
        self.print_data = show_stdout
        # delay to status updates in seconds
        self.loop_delay = screen_update_delay
        # delay to show messages
        self.msg_delay = msg_screen_time
        # manage queue by limiting how old the shown messages can be
        self.msg_max_time_diff = msg_timeout

    def setup_btns(self):
        for action in self.gpio_con.button_lines.keys():
            if self.gpio_con.button_lines[action] != None:
                if action == 'show_stats':
                    self.gpio_con.button_watcher(self.gpio_con.button_lines[action], self.show_stats_cb)

    # callback for show_stats button
    def show_stats_cb(self):
        if self.print_data:
            print("Show stats callback!")

    # main io loop
    async def io_loop(self):
        while True:
            if self.print_data:
                print(f"Timestamp: {self.wsc.timestamp} GPS: {self.wsc.gps_fix}")
            if self.i2c_disp != None:
                self.i2c_disp(self.wsc.timestamp, self.wsc.gps_fix)
            msg_shown = 0
            # check for error state
            if self.wsc.error_state > 0:
                print(self.wsc.error_msg)
            # check queue for messages
            elif not wsc.msgs.empty():
                while not wsc.msgs.empty():
                    # get message off queue
                    disp_msg = wsc.msgs.get()
                    # check the message timestamp
                    if disp_msg['ts'] == -1 or (self.wsc.timestamp - disp_msg['ts']) <= self.msg_max_time_diff:
                        if self.print_data:
                            print(disp_msg['text'])
                    await asyncio.sleep(self.msg_delay)
                    msg_shown = msg_shown + 1
                    # bail if showing another message with delay status update
                    if (msg_shown + 1) * self.msg_delay > self.loop_delay:
                        break
            await asyncio.sleep(self.loop_delay - (msg_shown * self.msg_delay))

#####
#####
##### Start OLD CODE
#Look for GPIO input
def input_watch(timeout):
    while True:
        print("Input Loop...")
        time.sleep(timeout)

#Look for kismet, start if not running, etc
def kismet_control():
    kismet_PID = NULL
    kismet_PID = find_process("kismet")
    if kismet_PID:
        print("Found kismet with PID {}".format)
        rgb_control(1)

#Find a process PID.
def find_process(processName):
    '''
    Get a list of all the PIDs of a all the running process whose name contains
    the given string processName
    '''
    listOfProcessObjects = []
    #Iterate over the all the running process
    for proc in psutil.process_iter():
       try:
           pinfo = proc.as_dict(attrs=['pid', 'name', 'create_time'])
           # Check if process name contains the given name string.
           if processName.lower() in pinfo['name'].lower() :
               listOfProcessObjects.append(pinfo)
       except (psutil.NoSuchProcess, psutil.AccessDenied , psutil.ZombieProcess) :
           pass
    return listOfProcessObjects;

def rgb_control(rgb_color):
    bus = smbus.SMBus(1)
    addr = 0x0d
    rgb_off_reg = 0x07
    rgb_effect_reg = 0x04
    rgb_speed_reg = 0x05
    rgb_color_reg = 0x06
    Max_LED = 3

    def setRGB(num, r, g, b):
        if num >= Max_LED:
            bus.write_byte_data(addr, 0x00, 0xff)
            bus.write_byte_data(addr, 0x01, r&0xff)
            bus.write_byte_data(addr, 0x02, g&0xff)
            bus.write_byte_data(addr, 0x03, b&0xff)
        elif num >= 0:
            bus.write_byte_data(addr, 0x00, num&0xff)
            bus.write_byte_data(addr, 0x01, r&0xff)
            bus.write_byte_data(addr, 0x02, g&0xff)
            bus.write_byte_data(addr, 0x03, b&0xff)

    def setRGBEffect(effect):
        if effect >= 0 and effect <= 4:
            bus.write_byte_data(addr, rgb_effect_reg, effect&0xff)
    def setRGBSpeed(speed):
        if speed >= 1 and speed <= 3:
            bus.write_byte_data(addr, rgb_speed_reg, speed&0xff)
    def setRGBColor(color):
        if color >= 0 and color <= 6:
            bus.write_byte_data(addr, rgb_color_reg, color&0xff)

    bus.write_byte_data(addr, rgb_off_reg, 0x00)
    #time.sleep(1)
    #0-water light, 1-breathing light, 2-marquee, 3-rainbow lights, 4-colorful lights
    setRGBEffect(1)
    #1-low speed, 2-medium speed (default), 3-high speed
    setRGBSpeed(3)
    #0-red, 1-green (default), 2-blue, 3-yellow, 4-purple, 5-cyan, 6-white
    setRGBColor(rgb_color)
    #Turn lED 1 RED
    #bus.write_byte_data(addr, 0x00, 0x00)
    #bus.write_byte_data(addr, 0x01, 0xFF)
    #bus.write_byte_data(addr, 0x02, 0x00)
    #bus.write_byte_data(addr, 0x03, 0x00)
    #Trun LED 2 GREEN
    #bus.write_byte_data(addr, 0x00, 0x01)
    #bus.write_byte_data(addr, 0x01, 0x00)
    #bus.write_byte_data(addr, 0x02, 0xFF)
    #bus.write_byte_data(addr, 0x03, 0x00)
    #Trun LED 3 BLUE
    #bus.write_byte_data(addr, 0x00, 0x02)
    #bus.write_byte_data(addr, 0x01, 0x00)
    #bus.write_byte_data(addr, 0x02, 0x00)
    #bus.write_byte_data(addr, 0x03, 0xFF)

#This will control the OLED display.
#Currently displays system stats, should be modified to show more relivant information
def oled_display():
    # Leaving the OLED on for a long period of time can damage it
    # Set these to prevent OLED burn in
    DISPLAY_ON  = 10 # on time in seconds
    DISPLAY_OFF = 50 # off time in seconds

    # Create the I2C interface.
    i2c = busio.I2C(SCL, SDA)

    # Create the SSD1306 OLED class.
    # The first two parameters are the pixel width and pixel height.  Change these
    # to the right size for your display!
    disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

    # Clear display.
    disp.fill(0)
    disp.show()

    # Create blank image for drawing.
    # Make sure to create image with mode '1' for 1-bit color.
    width = disp.width
    height = disp.height
    image = Image.new("1", (width, height))

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Draw some shapes.
    # First define some constants to allow easy resizing of shapes.
    padding = -2
    top = padding
    bottom = height - padding
    # Move left to right keeping track of the current x position for drawing shapes.
    x = 0


    # Load default font.
    font = ImageFont.load_default()

    # Alternatively load a TTF font.  Make sure the .ttf font file is in the
    # same directory as the python script!
    # Some other nice fonts to try: http://www.dafont.com/bitmap.php
    # font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)

    while True:

        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, width, height), outline=0, fill=0)

        # Shell scripts for system monitoring from here:
        # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
        cmd = "hostname -I | cut -d' ' -f1"
        IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
        cmd = 'cut -f 1 -d " " /proc/loadavg'
        CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
        cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'"
        MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")
        cmd = 'df -h | awk \'$NF=="/"{printf "Disk: %d/%d GB  %s", $3,$2,$5}\''
        Disk = subprocess.check_output(cmd, shell=True).decode("utf-8")

        # Write four lines of text.

        draw.text((x, top + 0), "IP: " + IP, font=font, fill=255)
        draw.text((x, top + 8), "CPU load: " + CPU, font=font, fill=255)
        draw.text((x, top + 16), MemUsage, font=font, fill=255)
        draw.text((x, top + 25), Disk, font=font, fill=255)

        # Display image.
        disp.image(image)
        disp.show()
        time.sleep(DISPLAY_ON)
        disp.fill(0)
        disp.show()
        time.sleep(DISPLAY_OFF)
#####
#####
##### End OLD CODE

if __name__ == "__main__":
    # load config
    config = configuration()

    eventloop = asyncio.get_event_loop()

    events = event_control()

    if config.debug_ws:
        print("Enabling trace on websocket-client")
        websocket.enableTrace(True)
    wsc = ws_connector(config.address, config.port, config.username, config.password,
                       reconnect=config.reconnect, reconnect_delay=config.reconnect_delay, debug=config.debug_ws)

    if config.local_process_management['enabled']:
        try:
            import psutil
        except:
            print("Failed to load psutil python3 module, required for local process management")
            sys.exit(1)
        # handle process management

    if config.local_gpio['enabled']:
        gpio = gpio_controller()

        if 'input_buttons' in config.local_gpio.keys():
            if 'enabled' in config.local_gpio['input_buttons'].keys() and config.local_gpio['input_buttons']['enabled']:
                if 'use_gpiozero' in config.local_gpio['input_buttons'].keys() and config.local_gpio['input_buttons']['use_gpiozero']:
                    try:
                        from gpiozero import Button
                    except:
                        print("Failed to load gpiozero python3 module. Installation is available from pip")
                        sys.exit(1)
                    gpio.configure_buttons(config.local_gpio['input_buttons'])
                else:
                    print("ERROR: In configuration 'input_buttons' is enabled but 'use_gpiozero' is not True")
                    print("Currently no other gpio libraries are supported! Skipping section.")
            else: print("'input_buttons' disabled in config.")
        else:
            print("In configuration 'local_gpio' is enabled, no 'input_buttons' sections found!")

        if 'leds' in config.local_gpio.keys():
            if 'enabled' in config.local_gpio['leds'].keys() and config.local_gpio['leds']['enabled']:
                if 'use_gpiozero' in config.local_gpio['leds'].keys() and config.local_gpio['leds']['use_gpiozero']:
                    try:
                        from gpiozero import LED
                    except:
                        print("Failed to load gpiozero python3 module. Installation is available from pip")
                        sys.exit(1)
                    gpio.configure_leds(config.local_gpio['leds'], events)
                else:
                    print("ERROR: In configuration 'leds' is enabled but 'use_gpiozero' is not True")
                    print("Currently no other gpio libraries are supported! Skipping section.")
            else: print("'leds' disabled in config.")
        else:
            print("In configuration 'local_gpio' is enabled, no 'leds' sections found!")

        if 'neopixels' in config.local_gpio.keys():
            if 'enabled' in config.local_gpio['neopixels'].keys() and config.local_gpio['neopixels']['enabled']:
                if not 'pin' in config.local_gpio['neopixels'].keys():
                    print("ERROR: In configuration 'neopixels' is enabled but 'pin' is not defined. Skipping")
                elif not 'pixels' in config.local_gpio['neopixels'].keys():
                    print("ERROR: In configuration 'neopixels' is enabled but 'pixels' is not defined. Skipping")
                else:
                    try:
                        import board
                    except:
                        print("Failed to load board python3 module. Please install Adafruit-Blinka from pip.")
                        sys.exit(1)
                    try:
                        import neopixel
                    except:
                        print("Failed to load neopixel python3 module. Please install adafruit-circuitpython-neopixel from pip")
                        sys.exit(1)
                    gpio.configure_neopixel(config.local_gpio['neopixels'], events)
            else: print("'neopixels' disabled in config.")
        else:
            print("In configuration 'local_gpio' is enabled, no 'neopixels' sections found!")
    else:
        gpio = None

    if config.i2c_display['enabled']:
        try:
            import busio, smbus
        except:
            print("Failed to load busio and/or smbus python3 modules, required for i2c display")
            sys.exit(1)
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as e:
            print("Failed to load PIL python3 module, required for i2c display")
            sys.exit(1)
        try:
            from board import SCL, SDA
        except Exception as e:
            print("Failed to load board python3 module, required for i2c display")
            sys.exit(1)
        if config.i2c_display['driver'] == 'adafruit_ssd1306':
            try:
                import adafruit_ssd1306
            except Exception as e:
                print("Failed to load adafruit_ssd1306 python3 module, required for i2c display driver")
                sys.exit(1)
        else:
            print("Incorrect setting for i2c_display 'driver': '{}'".format(config.i2c_display['driver']))
            print("Supported drivers are: 'adafruit_ssd1306'")
            sys.exit(1)
        if not 'width' in config.i2c_display.keys():
            print("No i2c_display 'width' set.")
            sys.exit(1)
        if not 'height' in config.i2c_display.keys():
            print("No i2c_display 'height' set.")
            sys.exit(1)
        try:
            display = i2c_controller(config.i2c_display['width'], config.i2c_display['height'])
        except:
            traceback.print_tb(err.__traceback__)
            print(err)
            print("ERROR: Failed creating display for i2c_display!")
            sys.exit(1)
    else:
        display = None

    # setup io controller
    io = io_controller(wsc, gpio, display, show_stdout=config.data_to_stdout)
    io.setup_btns()

    # create thread for websocket
    if config.debug:
        print("About to make ws thread")
    ws_thread = threading.Thread(target=wsc.ws_run)
    if config.debug:
        print("About to START ws thread")
    ws_thread.start()
    try:
        # run io in main thread
        if config.debug:
            print("Running io loop in main thread")
        eventloop.create_task(io.io_loop())
        eventloop.run_forever()
    except KeyboardInterrupt:
        # deinit pixels
        if gpio.np_running:
            try:
                gpio.pixels.deinit()
            except Exception as err:
                if config.debug:
                    traceback.print_tb(err.__traceback__)
                print(err)
                print("Error trying to deinit neopixels.")
        # shutdown thread
        wsc.reconnect = False
        wsc.ws.close()
        # wait for thread
        ws_thread.join()
    # both threads finished
    print("Program finished.")
