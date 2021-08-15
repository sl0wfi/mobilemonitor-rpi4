This file describes expected behavior of MobileMonitor. 

Startup:
The program will:
* Set all GPIO to default state
* Look for Kismet PID
* Attempt to connect to Kismet

### NeoPixels: (order is TBD)
Pixel 1: Websocket status
*   RED, solid : Not connected
*   GREEN, solid : Connected   

Pixel 2: GPS status
* RED, solid : No connection to GPSD
* YELLOW, blink : No Fix
* BLUE, solid : 2D fix
* GREEN, solid : 3D Fix

Pixel 3: SSID alert
* RED, blink : Unencrpted SSID
* YELLOW, blink : WEP SSID
* BLUE, blink : WPA/WPA2 SSID
* GREEN, blink : WPA3 SSID

Pixel 4: AP alert
* RED, blink : 
* YELLOW, blink
* BLUE, blink :
* GREEN, blink :

Pixel 5: WiFi Device alert
* RED, blink :
* YELLOW, blink : 
* BLUE, blink : 
* GREEN, blink : 

Pixel 6: Bluetooch device alert
* RED, blink : 
* YELLOW, blink : 
* BLUE, blink : 
* GREEN, blink : 

Pixel 7: Thermal alert
* RED, blink : Over 70c
* YELLOW, blink : Over 60c
* GREEN, solid : Under 60c

Pixel 8: Voltage alert
* RED, blink : Low voltage warning
* GREEN, solid : No warning
