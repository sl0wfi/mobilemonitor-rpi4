import websocket
import json
from collections import OrderedDict
import time
import multiprocessing
import sys

try:
    kismetIP = sys.argv[1]
    kismetUN = sys.argv[2]
    kismetPW = sys.argv[3]
except Exception as e:
    raise SystemExit(f"Usage: {sys.argv[0]} kismetIP kismetUN kismetPW")

def parse_msg(deser_msg):
    #print("Parsing a MESSAGE")
    print(deser_msg['MESSAGE']['kismet.messagebus.message_string']) #print the interesting bit

def on_message(ws, message):
    #print(message)
    #Put stuff here to parse messages and do stuff
    tsp = "TIMESTAMP"
    msg = "MESSAGE"
    deser_msg = json.loads(message)

    for key in deser_msg.keys():
        if key == tsp:
            print("Looks like a time stamp")
        if key == msg:
            print("Looks like a message")
            parse_msg(deser_msg)
    print("Message Parsed")

def on_error(ws, error):
    print(error)
    #Put stuff here to do stuff on an error

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")
    #Put stuff here for a closed socket

def on_open(ws):

    time.sleep(1)
    ws.send(json.dumps({"SUBSCRIBE":"MESSAGE"}))
    #time.sleep(1)
    #ws.send(json.dumps({"SUBSCRIBE":"TIMESTAMP"})) #Useful to verify connection during dev, but noisy

def ws_run(pid):
    ws = websocket.WebSocketApp("ws://{}:2501/eventbus/events.ws?user={}&password={}".format(kismetIP,kismetUN, kismetPW),
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
    p1 = multiprocessing.Process(target=ws_run, args=(1, ))
    p2 = multiprocessing.Process(target=input_watch, args=(3, ))

    # starting process 1
    p1.start()
    # starting process 2
    p2.start()

    # wait until process 1 is finished
    p1.join() #I do not want to wait
    # wait until process 2 is finished
    p2.join() #I do not want to wait

    # both processes finished
    print("Running...")
