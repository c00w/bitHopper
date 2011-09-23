#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import re
import ConfigParser
import sys
import random
import traceback
import pool_class
import eventlet
from eventlet.green import threading, os, time, socket

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

try:
    from collections import OrderedDict
except:
    OrderedDict = dict

class Pool_Parse():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.servers = {}
        self.initialized = False
        self.lock = threading.RLock()
        self.pool_configs = ['pools.cfg']
        self.started = False
        self.current_server = None
        with self.lock:
            self.loadConfig()
        self.bitHopper.db.pool = self

    def load_file(self, file_path, parser):
        try:
            # determine if application is a script file or frozen exe
            if hasattr(sys, 'frozen'):
                application_path = os.path.dirname(sys.executable)
            elif __file__:
                application_path = os.path.dirname(__file__)
            read = parser.read(os.path.join(application_path, file_path))
        except:
            read = parser.read(file_path)
        return read

    def loadConfig(self):
        parser = ConfigParser.SafeConfigParser()

        read = self.load_file('user.cfg', parser)
        if len(read) == 0:
            self.bitHopper.log_msg("user.cfg not found. You may need to move it from user.cfg.default")
            os._exit(1)

        userpools = parser.sections()

        for file_name in self.pool_configs:
            read = self.load_file(file_name, parser)
            if len(read) == 0:
                self.bitHopper.log_msg(file_name + " not found.")
                if self.initialized == False: 
                    os._exit(1)

        for pool in userpools:
            self.servers[pool] = pool_class.Pool(pool, dict(parser.items(pool)), self.bitHopper)

        for pool in parser.sections():
            try:
                if 'role' in dict(parser.items(pool)) and pool not in self.servers:
                    self.servers[pool] = pool_class.Pool(pool, dict(parser.items(pool)), self.bitHopper)
            except:
                continue

        # random UA strings
        try:
            if ( self.bitHopper.config.getboolean('main', 'use_random_ua') ):
                ua_strings = self.bitHopper.config.get('main', 'random_ua_list').split('|')
                for pool in self.servers:
                    if 'user_agent' not in self.servers[pool]:
                        idx = random.randint(0, len(ua_strings)-1)
                        self.servers[pool]['user_agent'] = ua_strings[idx]
        except:
            traceback.print_exc()


        if self.servers == {}:
            self.bitHopper.log_msg("No pools found in pools.cfg or user.cfg")

        if self.current_server is None: 
            self.current_server = pool

        self.bitHopper.db.check_database()
        #self.setup(self.bitHopper)
        
    def setup(self, bitHopper):
        with self.lock:
            self.bitHopper = bitHopper
                
            self.servers = OrderedDict(sorted(self.servers.items(), key=lambda t: t[1]['role'] + t[0]))
            self.build_server_map()
            if not self.started:
                self.bitHopper.api.update_api_servers()
                self.started = True
            
    def get_entry(self, server):
        if server in self.servers:
            return self.servers[server]
        else:
            return None

    def get_servers(self, ):
        return self.servers

    def get_current(self, ):
        return self.current_server

    def get_work_server(self):
        """A function which returns the server to query for work.
           Currently uses the donation server 1/100 times. 
           Can be configured to do trickle through to other servers"""
        value = random.randint(0,99)
        if value in self.server_map:
            result = self.server_map[value]
            if self.servers[result]['lag'] or self.servers[result]['role'] == 'disable':
                return self.get_current()
            else:
                return result
        else:
            return self.get_current()
                    
    def build_server_map(self):
        possible_servers = {}
        for server in self.servers:
            if 'percent' in self.servers[server]:
                possible_servers[server] = int(self.servers[server]['percent'])
        i = 0
        server_map = {}
        for k,v in possible_servers.items():
            for _ in xrange(v):
                server_map[i] = k
                i += 1
        self.server_map = server_map

    def set_current(self, server):
        self.current_server = server

if __name__ == "__main__":
    print 'Run python bitHopper.py instead.'
