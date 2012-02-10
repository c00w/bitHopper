#!/usr/bin/python
#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

import traceback, logging
import gevent
import time, threading

class APIAngel():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.interval = 60
        self.reincarnateInterval = 7200
        self.parseConfig()
        self.log_msg("Check interval: " + str(self.interval))
        self.log_msg("Re-Incarnate interval: " + str(self.reincarnateInterval))
        gevent.spawn(self.run)
        self.lock = threading.RLock()
            
    def parseConfig(self):
        try:
            self.interval = self.bitHopper.config.getint('plugin.apiangel', 'interval')
            self.reincarnateInterval = self.bitHopper.config.getint('plugin.apiangel', 'reincarnateInterval')
        except:
            traceback.print_exc()
        
    def log_msg(self, msg, **kwargs):
        logging.info(msg)
        
    def log_dbg(self, msg, **kwargs):
        logging.debug(msg)
        
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
            gevent.sleep(self.interval)
