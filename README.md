# mobilemonitor-rpi4
A collection of tools to manage a mobile wireless monitoring platform. Monitors and manages state of hardware and software, accepts input via physical interaction and provides visual, auditory, and/or haptic output.


### **This project is under development. And is likely to be broken at any moment.**

## **Goals**

This project aims to creat a platform for war driving/biking/walking/boating...whatever without the need for a screen and keyboard. The user may still connect to the (wonderful) Kismet web interface for more functionality. The list below is incomplete, as is the code. 

### **OUTPUT**

The primary motivator for this project is to monitor system health and be able to attempt some corrective actions. The discovery notifications via LEDs are just fun blinkin' lights. 

* Kismet status - Text on OLED, RGB LED
* GPS Status - Text on OLED, RGB LED
* Various Kismet discovery alerts - RGB LEDs, Buzzers, potentially haptics.
* Number of discovered devices, SSIDs, etc (alternate status screen)
* Interfaces currently used by Kismet (alternate status screen) 

### **INPUT**

Buttons via GPIO. This is a list of posibilites, platform may not have this many buttons. 
* Safe system shut down
* Shut down Kismet - Save battery in uninteresting areas
* Restart Kismet for new run
* Network and USB reset without reboot
* Note point of interest - Logs GPS location and time
* Enable / Disable WiFi hotspot using Raspberry Pi onboard WiFi

### **Hardware**

This is tested on a Raspberry Pi 4, 4GB. It will work on a 2GB model but you may see reduced performance in Kismet. Not tested on 8GB, but baring any add incompatibilies it should work. 

The text output is deisgned for the ubiqiutous 128x32 OLED modules availble everywhere. Example is the Adafruit PiOLED - 128x32 Monochrome OLED. This communicates via I2C to display various interesing information. 

The (planned) RGB LED ouput is based on WS2812 LEDs (like a NeoPixle). The system uses eight (8) LEDs by default.

Long term plan is to support other boards. This project is very new, but boards from Pine64 and Radxa are likely the first development targets after the Pi 4. 

### **Setup on kali as of July 2021**

**NOTE: Kali does note have convenient way of enabling the I2C on the Pi4. You need to folow the procedure below to get the OLED screen working. 

* #sudo apt-get install python3-pip
* #sudo pip3 install websocket-client
* #sudo pip3 install adafruit-circuitpython-ssd1306
* #sudo pip3 install adafruit-blinka
* #sudo pip3 install psutil
* #sudo pip3 install requests
* #sudo pip3 install gpiozero

#### Configuring I2C Manually

Source: https://github.com/fivdi/i2c-bus/blob/master/doc/raspberry-pi-i2c.md

On older versions of Raspbian (prior to Raspbian Jessie 2015-11-21) the raspi-config tool can still be used to configure the I2C bus, but additional steps typically need to be performed.

Step 1 - Enable I2C
To enable I2C ensure that /boot/config.txt contains the following line:

dtparam=i2c_arm=on

Step 2 - Enable user space access to I2C
To enable userspace access to I2C ensure that /etc/modules contains the following line:

i2c-dev

Step 3 - Setting the I2C baudrate
The default I2C baudrate is 100000. If required, this can be changed with the i2c_arm_baudrate parameter. For example, to set the baudrate to 400000, add the following line to /boot/config.txt:

dtparam=i2c_arm_baudrate=400000

Step 4 - I2C access without root privileges
If release 2015-05-05 or later of the Raspbian Operating System is being used, this step can be skipped as user pi can access the I2C bus without root privileges.

If an earlier release of the Raspbian Operating System is being used, create a file called 99-i2c.rules in directory /etc/udev/rules.d with the following content:

SUBSYSTEM=="i2c-dev", MODE="0666"

This will give all users access to I2C and sudo need not be specified when executing programs using i2c-bus. A more selective rule should be used if required.

Step 5 - Reboot the Raspberry Pi
After performing the above steps, reboot the Raspberry Pi.
