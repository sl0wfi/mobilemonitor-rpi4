# Import libraries

import websocket
import json
import time
import threading
import multiprocessing
import sys
import RPi.GPIO as GPIO

#Set the mode of the GPIO libaray to use the BCM pin numbers, not the board numbers.
GPIO.setmode(GPIO.BCM)

#Set the GPIO BCM pin numbers to be used for each function
buzzer = 18
led_SSID = 23
led_AP = 24
led_client = 25
led_GPS = 12 #This is a good candidate for a RGBW LED - RED=no GSPSd connection, YELLOW=GPSd connected but no lock, GREEN= GPS locked

try:
    kismetIP = sys.argv[1]
    kismetUN = sys.argv[2]
    kismetPW = sys.argv[3]
except Exception as e:
    raise SystemExit(f"Usage: {sys.argv[0]} kismetIP kismetUN kismetPW")

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

def on_message(ws, message):
    #print(message)
    #Put stuff here to parse messages and do stuff
    tsp = "TIMESTAMP" # String to recognize a timestamp message
    msg = "MESSAGE" #String to recognize a message message
    deser_msg = json.loads(message)

    for key in deser_msg.keys():
        if key == tsp:
            print("Looks like a time stamp")
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
    print("Connected to kisemt at {}".format(kismetIP))
    time.sleep(1)
    ws.send(json.dumps({"SUBSCRIBE":"MESSAGE"}))
    #time.sleep(1)
    #ws.send(json.dumps({"SUBSCRIBE":"TIMESTAMP"})) #Useful to verify connection during dev, but noisy

def ws_run():
    ws = websocket.WebSocketApp("ws://{}:2501/eventbus/events.ws?user={}&password={}".format(kismetIP,kismetUN,kismetPW),
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    ws.run_forever()

def input_watch(timeout):
    while True:
        print("Input Loop...")
        time.sleep(timeout)


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
