import websocket
import json
import time
# importing the multiprocessing module
import multiprocessing
import sys

kismetUN = sys.argv[1]
kismetPW = sys.argv[2]


def on_message(ws, message):
    print(message)
    #Put stuff here to parse messages and do stuff

def on_error(ws, error):
    print(error)
    #Put stuff here to do stuff on an error

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")
    #Put stuff here for a closed socket

def on_open(ws):
    #def run(*args):
        #for i in range(3):
        time.sleep(1)
        ws.send(json.dumps({"SUBSCRIBE":"MESSAGE"}))
        time.sleep(1)
        #ws.send(json.dumps({"SUBSCRIBE":"TIMESTAMP"})) #Useful to verify connection during dev, but noisy
        #time.sleep(1)

        #ws.close() #I do not understand why this is here, in the on_open function?!? Maybe for threading?
        #print("thread terminating...")
    #thread.start_new_thread(run, ())

def ws_run(pid):
    ws = websocket.WebSocketApp("ws://localhost:2501/eventbus/events.ws?user={}&password={}".format(kismetUN, kismetPW),
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    ws.run_forever()

def print_loop(pid):
    while True:
        print("Print Loop...")
        time.sleep(1)


if __name__ == "__main__":
    #websocket.enableTrace(True)
    # creating processes
    p1 = multiprocessing.Process(target=ws_run, args=(1, ))
    #p2 = multiprocessing.Process(target=print_cube, args=(10, ))

    # starting process 1
    p1.start()
    # starting process 2
    #p2.start()

    # wait until process 1 is finished
    #p1.join() #I do not want to wait
    # wait until process 2 is finished
    #p2.join() #I do not want to wait

    # both processes finished
    print("Done!")
