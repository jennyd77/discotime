#!/usr/bin/env python

import time
import json
import RPi.GPIO as GPIO
import threading
import sys
import logging
import getopt
sys.path.append("aws-iot-device-sdk-python")
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
from disco import DoorDevice, DiscoDevice

OUTPIN=13
DOORPIN=23
DOORCLOSED=True
SONG_DURATION=30

# this function is a callback we will pass in to an instance of
# DoorPollingThread, which will call us when it detects a change in
# the GPIO door pin state

def door_moved(door, state, previous_event_time, current_event_time):
        state_change_time = time.time()
        #print("duration of last state = " + str(current_event_time - previous_event_time))
        DOORCLOSED=state
        if (DOORCLOSED):
                print("Door is closed, it was open for",str(current_event_time - previous_event_time))
                #payload = '{"state":{"reported":{"doorstate":"closed","timeopen":' + str(current_event_time - previous_event_time) + '}}}'
                #print("payload is ",json.dumps(payload))
                print("sending desired state to shadow")
                #door.sendShadowUpdate(payload)
                door.close()
        else:
                print("Door is open")
                #payload = '{"state":{"reported":{"doorstate":"open","timeopen":0}}}'
                #print("payload is ",json.dumps(payload))
                print("sending desired state to shadow")
                #door.sendShadowUpdate(payload)
                door.open()
        
class DoorPollingThread(threading.Thread):
        def __init__(self, door_state_changed_fn, door_pin, door):
                super().__init__(group=None)
                self._door_pin = door_pin
                self._door = door
                self._door_state_changed_fn = door_state_changed_fn
                self._stop_event = threading.Event()

        # use a thread Event instance member to allow callers to tell
        # us to stop the polling loop in the thread run member
        def stop_polling(self):
                self._stop_event.set()

        # this thread class's run method just loops until the calling
        # thread tells us to stop
        def run(self):
                last_event_time = time.time()
                last_door_state = GPIO.input(DOORPIN)
                while not self._stop_event.is_set():
                        self._stop_event.wait(0.2)
                        GPIO.setmode(GPIO.BCM)
                        GPIO.setup(DOORPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                        current_door_state = GPIO.input(DOORPIN)
                        if last_door_state != current_door_state:
                                current_event_time = time.time()
                                self._door_state_changed_fn(self._door, current_door_state, last_event_time, current_event_time)
                                last_event_time = current_event_time
                                last_door_state = current_door_state
                        
                                
                                
#print("GPI library version: " + GPIO.VERSION)

#GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
GPIO.setup(OUTPIN, GPIO.OUT)
GPIO.output(OUTPIN, GPIO.HIGH)
GPIO.setup(DOORPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

door = DoorDevice()
door.connectDeviceShadow()

disco = DiscoDevice()
disco.connectDeviceShadow()

print("door device connected, listening...")

try:
        door_thread = DoorPollingThread(door_moved, DOORPIN, door)
        door_thread.start()
        
        while True:
                time.sleep(1)
                
except KeyboardInterrupt:
        GPIO.cleanup()

door_thread.stop_polling()

GPIO.cleanup()

