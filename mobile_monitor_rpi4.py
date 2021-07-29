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
#!/usr/bin/env python3
# Import libraries

try:
    import sys, json, time, threading, subprocess, psutil, busio, smbus, asyncio
except Exception as e:
    print("Failed to load some module, check that you have sys, json, time, threading, subprocess, psutil, busio, smbus, asyncio")
    sys.exit(1)

from queue import Queue
from board import SCL, SDA
#import multiprocessing
try:
    from gpiozero import LED, Button
except Exception as e:
    print("Failed to load gpiozero python3 module. Installation is available from pip")
    sys.exit(1)
try:
    import websocket
except Exception as e:
    print("Failed to load websocket python3 module. Installation is available: pip install websocket-client")
    sys.exit(1)
try:
    from PIL import Image, ImageDraw, ImageFont
except Exception as e:
    print("Failed to load PIL python3 module. installation is available from pip3")
    sys.exit(1)
try:
    import adafruit_ssd1306
except Exception as e:
    print("Failed to load adafruit_ssd1306 python3 module. installation is available from pip3")
    sys.exit(1)

# class for io loop
class io_controller(object):
    # init with configuration
    def __init__(self, ws_connector, screen_update_delay=3, msg_screen_time=1, msg_timeout=10):
        self.buzzer = 18
        self.led_SSID = LED(23)
        self.led_AP = LED(24)
        self.led_client = LED(25)
        self.led_GPS = LED(12)
        # reference to ws_connector instance to read status from
        self.wsc = ws_connector
        # delay to status updates in seconds
        self.loop_delay = screen_update_delay
        # delay to show messages
        self.msg_delay = msg_screen_time
        # manage queue by limiting how old the shown messages can be
        self.msg_max_time_diff = msg_timeout

    # handle actual io
    # output right now is print to standard out
    def io_loop(self):
        # Leaving the OLED on for a long period of time can damage it
        # Set these to prevent OLED burn in
        self.DISPLAY_ON  = 2 # on time in seconds
        self.DISPLAY_OFF = 58 # off time in seconds

        # Create the I2C interface.
        self.i2c = busio.I2C(SCL, SDA)

        # Create the SSD1306 OLED class.
        # The first two parameters are the pixel width and pixel height.  Change these
        # to the right size for your display!
        self.disp = adafruit_ssd1306.SSD1306_I2C(128, 32, self.i2c)

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

        # Alternatively load a TTF font.  Make sure the .ttf font file is in the
        # same directory as the python script!
        # Some other nice fonts to try: http://www.dafont.com/bitmap.php
        # font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)
        while True:

            # Draw a black filled box to clear the image.
            self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

            # Shell scripts for system monitoring from here:
            # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
            self.cmd = "hostname -I | cut -d' ' -f1"
            self.IP = subprocess.check_output(self.cmd, shell=True).decode("utf-8")
            self.cmd = 'cut -f 1 -d " " /proc/loadavg'
            self.CPU = subprocess.check_output(self.cmd, shell=True).decode("utf-8")
            self.cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'"
            self.MemUsage = subprocess.check_output(self.cmd, shell=True).decode("utf-8")
            self.cmd = 'df -h | awk \'$NF=="/"{printf "Disk: %d/%d GB  %s", $3,$2,$5}\''
            self.Disk = subprocess.check_output(self.cmd, shell=True).decode("utf-8")

            # Write four lines of text.

            self.draw.text((self.x, self.top + 0), "GPS: " + self.wsc.gps_fix, font=self.font, fill=255)
            self.draw.text((self.x, self.top + 8), "TS: " + str(self.wsc.timestamp), font=self.font, fill=255)
            self.draw.text((self.x, self.top + 16), self.MemUsage, font=self.font, fill=255)
            self.draw.text((self.x, self.top + 25), self.Disk, font=self.font, fill=255)

            # Display image.
            self.disp.image(self.image)
            self.disp.show()
            #time.sleep(self.DISPLAY_ON)
            #self.disp.fill(0)
            #self.disp.show()
            #time.sleep(self.DISPLAY_OFF)

            print(f"Timestamp: {self.wsc.timestamp} GPS: {self.wsc.gps_fix}")
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
                        print(disp_msg['text'])
                    time.sleep(self.msg_delay)
                    msg_shown = msg_shown + 1
                    # bail if showing another message with delay status update
                    if (msg_shown + 1) * self.msg_delay > self.loop_delay:
                        break
            time.sleep(self.loop_delay - (msg_shown * self.msg_delay))

class ws_connector(object):
    # init the variables for the class
    def __init__(self, addr, un, pw):
        self.kismetIP = addr
        self.kismetUN = un
        self.kismetPW = pw
        self.reconnect = True
        self.reconnect_delay = 3

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
        if "SSID" in msg_str:
            io_msg = "Found new SSID"
        if "new 802.11 Wi-Fi access point" in msg_str:
            io_msg = "Found new access point"
        # see if we have a message for io, put on queue
        if not io_msg is None:
            self.msgs.put({'text': io_msg, 'ts': self.timestamp})

    # parse eventbus message to create message for io display
    def parse_gps(self, msg_dict):
        gps_msg = msg_dict['GPS_LOCATION']['kismet.common.location.fix']
        if gps_msg == 3:
            self.gps_fix = "3D fix"
        elif gps_msg == 2:
            self.gps_fix = "2D fix"
        else:
            self.gps_fix = "NO LOCK"

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
    # i assume this is a protocol error of some sort (meaning ws is still connected)
    # this has not been tested and not sure it is being handled correctly
    def on_error(self, ws, error):
        # signal error state and provide an error message
        self.error_state = 1
        self.error_msg = type(error).__name__

    # ws client callback for closed connection
    def on_close(self, ws, close_status_code, close_msg):
        # reset status variables
        self.reset_status()
        # signal error state and provide a hopeful error message
        self.error_state = 1
        self.error_msg = "Connection closed, will retry in {} seconds".format(self.reconnect_delay)

    # ws client callback for opened connection
    def on_open(self, ws):
        # clear error state and error message
        self.error_state = 0
        self.error_msg = ''

        # put connect message on queue
        self.msgs.put({'text': "Connected to kismet at {}".format(self.kismetIP), 'ts': self.timestamp})

        # send eventbus subscribes
        time.sleep(1)
        ws.send(json.dumps({"SUBSCRIBE":"MESSAGE"}))
        time.sleep(1)
        ws.send(json.dumps({"SUBSCRIBE":"TIMESTAMP"}))
        time.sleep(1)
        ws.send(json.dumps({"SUBSCRIBE":"GPS_LOCATION"}))

    # method to run ws client
    def ws_run(self):
        print("Starting websocket connection")
        self.ws = websocket.WebSocketApp("ws://{}:2501/eventbus/events.ws?user={}&password={}".format(self.kismetIP,self.kismetUN,self.kismetPW),
                                on_open=self.on_open,
                                on_message=self.on_message,
                                on_error=self.on_error,
                                on_close=self.on_close)
        # use infinite loop to restart (avoids stack overflow from recursion in on_close cb)
        while True:
            self.ws.run_forever()
            if self.reconnect:
                time.sleep(3)
            else:
                break
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
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <Kismet address> <Kismet username> <Kismet password>")
        sys.exit(1)
    #websocket.enableTrace(True)
    wsc = ws_connector(sys.argv[1], sys.argv[2], sys.argv[3])
    io = io_controller(wsc)
    # create thread for websocket
    print("About to make ws thread")
    ws_thread = threading.Thread(target=wsc.ws_run)
    print("About to START ws thread")
    ws_thread.start()
    try:
        # run io in main thread
        print("About to START io thread")
        io.io_loop()
    except KeyboardInterrupt:
        # shutdown thread
        wsc.reconnect = False
        wsc.ws.close()
        # wait for thread
        ws_thread.join()
    # both threads finished
    print("Program finished.")
