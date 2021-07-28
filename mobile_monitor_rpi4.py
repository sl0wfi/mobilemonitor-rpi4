#!/usr/bin/env python3

import sys, time, json, threading
from queue import Queue
try:
    import websocket
except:
    print("Failed to import python3 module 'websocket'.")
    print("Install using 'apt-get install python3-websocket' or 'pip3 install websocket-client'")
    sys.exit(1)

# define class to handle websocket, provide a name space for variables and methods
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
            self.gps_fix = "GPS has 3d fix"
        elif gps_msg == 2:
            self.gps_fix = "GPS has 2d fix"
        else:
            self.gps_fix = "GPS not available"

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

# class for io loop
class io_controller(object):
    # init with configuration
    def __init__(self, ws_connector, screen_update_delay=3, msg_screen_time=1, msg_timeout=10):
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
        while True:
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

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <Kismet address> <Kismet username> <Kismet password>")
        sys.exit(1)

    #websocket.enableTrace(True)
    wsc = ws_connector(sys.argv[1], sys.argv[2], sys.argv[3])
    io = io_controller(wsc)

    # create thread for websocket
    ws_thread = threading.Thread(target=wsc.ws_run)
    ws_thread.start()

    try:
        # run io in main thread
        io.io_loop()
    except KeyboardInterrupt:
        # shutdown thread
        wsc.reconnect = False
        wsc.ws.close()
        # wait for thread
        ws_thread.join()

    # both threads finished
    print("Program finished.")
