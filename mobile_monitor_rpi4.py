#This file written by sl0wfi
#Many thanks to notaco as large chunks of this are from https://github.com/notaco/kismet_status_leds.py

# Import libraries
try:
    import websockets
except Exception as e:
    print("Failed to load websockets python3 module. installation is available from pip")
    sys.exit(1)

import json
import time
import subprocess
import threading
import multiprocessing
import sys
import psutil
import RPi.GPIO as GPIO

from board import SCL, SDA
import busio
import smbus
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

#Set the mode of the GPIO libaray to use the BCM pin numbers, not the board numbers.
GPIO.setmode(GPIO.BCM)

#Set the GPIO BCM pin numbers to be used for each function
buzzer = 18
led_SSID = 23
led_AP = 24
led_client = 25
led_GPS = 12 #This is a good candidate for a RGBW LED - RED=no GSPSd connection, YELLOW=GPSd connected but no lock, GREEN= GPS locked


#This is launch argument processing but it is terrible.
#Need to migrate to a proper argument parser
try:
    kismetIP = sys.argv[1]
    kismetUN = sys.argv[2]
    kismetPW = sys.argv[3]
except Exception as e:
    raise SystemExit(f"Usage: {sys.argv[0]} kismetIP kismetUN kismetPW")

#Parser for MESSGE messages.
#Messages come here if they are a MESSAGE and then are parsed more
def parse_msg(msg_dict):
    #print("Parsing a MESSAGE")
    #print(deser_msg['MESSAGE']['kismet.messagebus.message_string']) #print the interesting bit
    msg_str = msg_dict['MESSAGE']['kismet.messagebus.message_string']
    #print(msg_str)
    if "SSID" in msg_str:
        print("Found new SSID")
        #put code here to blink led_SSID

    if "new 802.11 Wi-Fi access point" in msg_str:
        print("Found new access point")
        #put code here to blink led_AP

    if "Connected to gpsd server" in msg_str:
        print("GPS Connection Success")
        #put code here to set GPS LED to YELLOW

#Initial message parsing. This will determine the type of message and call additional parsing as needed.
def on_message(ws, message):
    #print(message)
    #Put stuff here to parse messages and do stuff
    tsp = "TIMESTAMP" # String to recognize a timestamp message
    msg = "MESSAGE" #String to recognize a message message
    deser_msg = json.loads(message)

    for key in deser_msg.keys():
        if key == tsp:
            print("Looks like a time stamp")
            #Add and call function to parse TIMESTAMP messages
        if key == msg:
            print("Looks like a message")
            parse_msg(deser_msg)
    print("Message Parsed")

def on_error(ws, error):
    print("Connection Error")
    print(error)
    #Put stuff here to do stuff on an error

def on_close(ws, close_status_code, close_msg):
    #print("### closed ###")
    print("Connection closed, will rety in 3 seconds")
    #print ("Retry : %s" % time.ctime())
    time.sleep(3)
    ws_run() # retry per 10 seconds
    #Put stuff here for a closed socket

def on_open(ws):
    print("Connected to kismet at {}".format(kismetIP))
    time.sleep(1)
    ws.send(json.dumps({"SUBSCRIBE":"MESSAGE"}))
    #time.sleep(1)
    #ws.send(json.dumps({"SUBSCRIBE":"TIMESTAMP"})) #Useful to verify connection during dev, but noisy

#This needs to be updated to use the new library
def ws_run():
    ws = websocket.WebSocketApp("ws://{}:2501/eventbus/events.ws?user={}&password={}".format(kismetIP,kismetUN,kismetPW),
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    ws.run_forever()

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

if __name__ == "__main__":
    #websocket.enableTrace(True)
    # creating processes

    p1 = multiprocessing.Process(target=ws_run)
    p2 = multiprocessing.Process(target=input_watch, args=(3,))

    # starting process 1
    p1.start()
    # starting process 2
    p2.start()

    # wait until process 1 is finished
    p1.join()
    # wait until process 2 is finished
    p2.join()

    # both processes finished
    print("Program finished.")
