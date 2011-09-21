#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import re
import ConfigParser
import sys
import random
import traceback

import eventlet
from eventlet.green import threading, os, time, socket

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

try:
    from collections import OrderedDict
except:
    OrderedDict = dict

class Pool():
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
            self.servers[pool] = dict(parser.items(pool))

        for pool in parser.sections():
            try:
                if 'role' in dict(parser.items(pool)) and pool not in self.servers:
                    self.servers[pool] = dict(parser.items(pool))
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
        if self.started == True:
            self.bitHopper.db.check_database()
            self.setup(self.bitHopper)
        
    def setup(self, bitHopper):
        with self.lock:
            self.bitHopper = bitHopper
            for server in self.servers:
                self.servers[server]['shares'] = int(bitHopper.difficulty.get_difficulty())
                self.servers[server]['ghash'] = -1
                self.servers[server]['duration'] = -1
                self.servers[server]['duration_temporal'] = 0
                self.servers[server]['isDurationEstimated'] = False
                self.servers[server]['last_pulled'] = time.time()
                self.servers[server]['lag'] = False
                self.servers[server]['api_lag'] = False
                
                refresh_limit = self.bitHopper.config.getint('main', 'pool_refreshlimit')
                if 'refresh_time' not in self.servers[server]:
                    self.servers[server]['refresh_time'] = refresh_limit
                else:
                    self.servers[server]['refresh_time'] = int(self.servers[server]['refresh_time'])
                if 'refresh_limit' not in self.servers[server]:
                    self.servers[server]['refresh_limit'] = refresh_limit
                else:
                    self.servers[server]['refresh_limit'] = int(self.servers[server]['refresh_limit'])
                self.servers[server]['rejects'] = self.bitHopper.db.get_rejects(server)
                self.servers[server]['user_shares'] = self.bitHopper.db.get_shares(server)
                self.servers[server]['payout'] = self.bitHopper.db.get_payout(server)
                self.servers[server]['expected_payout'] = self.bitHopper.db.get_expected_payout(server)
                if 'api_address' not in self.servers[server]:
                    self.servers[server]['api_address'] = server
                if 'name' not in self.servers[server]:
                    self.servers[server]['name'] = server
                if 'role' not in self.servers[server]:
                    self.servers[server]['role'] = 'disable'
                if self.servers[server]['role'] in ['mine_slush']:
                    self.servers[server]['role'] = 'mine_c'
                    self.servers[server]['c'] = 300
                if 'lp_address' not in self.servers[server]:
                    self.servers[server]['lp_address'] = None
                self.servers[server]['err_api_count'] = 0
                self.servers[server]['pool_index'] = server
                self.servers[server]['default_role'] = self.servers[server]['role']
                if self.servers[server]['default_role'] in ['info','disable']:
                    self.servers[server]['default_role'] = 'mine'

                #Coin Handling
                if 'coin' not in self.servers[server]:
                    if self.servers[server]['role'] in ['mine', 'info', 'backup', 'backup_latehop', 'mine_charity', 'mine_c']:
                        coin_type = 'btc'
                    elif self.servers[server]['role'] in ['mine_nmc']:
                        coin_type = 'nmc'
                    elif self.servers[server]['role'] in ['mine_ixc']:
                        coin_type = 'ixc'
                    elif self.servers[server]['role'] in ['mine_i0c']:
                        coin_type = 'i0c'
                    elif self.servers[server]['role'] in ['mine_scc']:
                        coin_type = 'scc'   
                    else:
                        coin_type = 'btc'
                    self.servers[server]['coin'] = coin_type
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
