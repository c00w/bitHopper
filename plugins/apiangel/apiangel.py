#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import traceback

import time
import eventlet
from eventlet.green import time, threading

class APIAngel():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.interval = 60
        self.reincarnateInterval = 7200
        self.parseConfig()
        self.log_msg(" - Check interval: " + str(self.interval))
        self.log_msg(" - Re-Incarnate interval: " + str(self.reincarnateInterval))
        eventlet.spawn_n(self.run)
        self.lock = threading.RLock()
            
    def parseConfig(self):
        try:
            self.interval = self.bitHopper.config.getint('plugin.apiangel', 'interval')
            self.reincarnateInterval = self.bitHopper.config.getint('plugin.apiangel', 'reincarnateInterval')
        except:
            traceback.print_exc()
        
    def log_msg(self, msg, **kwargs):
        self.bitHopper.log_msg(msg)
        
    def log_dbg(self, msg, **kwargs):
        self.bitHopper.log_dbg(msg)
        
    def run(self):
        while True:
            now = time.time()
            for server in self.bitHopper.pool.servers:
                info = self.bitHopper.pool.get_entry(server)
                if info['role'] == 'api_disable':
                    delta = now - info['last_pulled']
                    self.log_dbg( 'Check api_disable server: ' + server + ' last_pulled: ' + str(info['last_pulled']) + ' / ' + str(now) + ' delta: ' + str(delta) )                    
                    if delta > self.reincarnateInterval:
                        self.log_msg('Restoring server: ' + server)
                        info['role'] = info['default_role']
            eventlet.sleep(self.interval)
