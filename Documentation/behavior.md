This file describes expected behavior of MobileMonitor.

### Startup:
The program will:
* Set all GPIO to default state
* Initialize NeoPixels, show some output to each
* Look for Kismet PID, if not found start kismet. If kismet does not start, output information to i2c and blink all neopixels red.
* Attempt to connect to Kismet

### Buttons
* Hold a button to change i2c display to alternate information
* Press a button to shut down kismet, press again to restart kismet
* Press a button to run "I'm Home" tasks: Connect to known SSID, transfer collected data to somewhere: HTTPS, FTP, NFS, etc.  
* Hold a button for 5 seconds to initiate system shutdown.

### i2c Display - Primary information (Kismet status)
* Websocket connection status
* GPS status
* Packet stream
* uptime

### i2c Display - Alternate information (System status)
* Alternate information display can be activated by holding a button
* CPU load, RAM usage (as %), disk usage (as %)
* CPU temperature
* Low voltage warning  

### NeoPixels: (order is TBD)
Pixel 1: Websocket status
* RED, solid : Not connected
* YELLOW, solid : Authentication failure
* GREEN, solid : Connected   

Pixel 2: GPS status
* RED, solid : No connection to GPSD
* YELLOW, blink : No Fix
* BLUE, solid : 2D fix
* GREEN, solid : 3D Fix

Pixel 3: SSID alert
* RED, blink : Unencrypted SSID
* YELLOW, blink : WEP SSID
* BLUE, blink : WPA/WPA2 SSID
* GREEN, blink : WPA3 SSID

Pixel 4: AP alert
* RED, blink :
* YELLOW, blink
* BLUE, blink : New AP found
* GREEN, blink :

Pixel 5: WiFi Device alert
* RED, blink :
* YELLOW, blink :
* BLUE, blink :
* GREEN, blink : New device found

Pixel 6: Bluetooth device alert
* RED, blink :
* YELLOW, blink :
* BLUE, blink : New bluetooth device found
* GREEN, blink :

Pixel 7: Thermal alert
* RED, blink : Over 70c
* YELLOW, blink : Over 60c
* GREEN, solid : Under 60c

Pixel 8: Voltage alert
* RED, blink : Low voltage warning
* GREEN, solid : No warning
