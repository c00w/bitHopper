#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

import json, re, ConfigParser, sys, random, traceback, logging
import pool_class
import gevent
import threading, os, time, socket

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
        self.pool_configs = ['pools.cfg', 'pools-custom.cfg']
        self.started = False
        self.current_list = []
        self.server_map = {}
        self.i = 0
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
            logging.info("user.cfg not found. You may need to move it from user.cfg.default")
            os._exit(1)

        userpools = parser.sections()

        read_items = 0
        for file_name in self.pool_configs:
            read = self.load_file(file_name, parser)
            read_items += len(read)
            if len(read) == 0:
                logging.info(file_name + " not found.")
                
        if self.initialized == False: 
            if read_items == 0:
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
            logging.info("No pools found in pools.cfg or user.cfg")

        if len(self.current_list) == 0: 
            self.current_list = [pool]

        self.bitHopper.db.check_database()
        #self.setup(self.bitHopper)
        
    def setup(self, bitHopper):
        with self.lock:
            self.bitHopper = bitHopper
                
            self.servers = OrderedDict(sorted(self.servers.items(), key=lambda t: t[1]['role'] + t[0]))
            self.bitHopper.select_best_server()
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
        return self.get_work_server()

    def get_work_server(self):
        """A function which returns the server to query for work.
           Take the server map and cycles through it"""
        value = self.i
        self.i = (self.i +1) % 100
        if value in self.server_map:
            result = self.server_map[value]
            if self.servers[result]['lag'] or self.servers[result]['role'] == 'disable':
                return self.current_list[0]
            else:
                return result
        else:
            return self.current_list[0]
                    
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
        while i <= 99:
            server_map[i] = self.current_list[i%len(self.current_list)]
            i += 1
        self.server_map = server_map

    def set_current(self, server):
        self.current_server = server

if __name__ == "__main__":
    print 'Run python bitHopper.py instead.'
