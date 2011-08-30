#License#
#bitHopper by Colin Rice is licensed under a 
#Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.
"""Implements a system for api callbacks"""
import eventlet
from eventlet.green import threading

class Callback():
    def __init__(self):
        self.functions = []
        self._lock = threading.RLock()

    def add_function(self, function):
        with self._lock:
            self.functions.append(function)

    def remove_function(self, function):
        with self._lock:
            self.functions.remove(function)
    
    def call(self, * args, ** kwargs):
        with self._lock:
            for item in self.functions:
                eventlet.spawn_n(item, args, kwargs)

class API():
    """Main class for accessing api callbacks.
       Should be accesible from bitHopper.api"""
    def __init__(self):
        self.callbacks = {}

    def new_callback(self, name):
        self.callbacks[name] = Callback()

    def add_callback(self, name, func):
        self.callbacks[name].add_function(func)

    def remove_callback(self, name, func):
        self.callbacks[name].remove_function(func)

    def callback(self, name, *args, ** kwargs):
        self.callbacks[name].call(args, kwargs)

