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
        self.api_pull = ['mine', 'info', 'mine_slush', 'mine_nmc', 'mine_ixc', 'mine_i0c',  'mine_scc', 'mine_charity', 'mine_deepbit', 'backup', 'backup_latehop']
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
                if 'lp_address' not in self.servers[server]:
                    self.servers[server]['lp_address'] = None
                self.servers[server]['err_api_count'] = 0
                self.servers[server]['pool_index'] = server
                self.servers[server]['default_role'] = self.servers[server]['role']
                if self.servers[server]['default_role'] in ['info','disable']:
                    self.servers[server]['default_role'] = 'mine'

                #Coin Handling
                if 'coin' not in self.servers[server]:
                    if self.servers[server]['role'] in ['mine', 'info', 'backup', 'backup_latehop', 'mine_charity', 'mine_slush']:
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
                self.update_api_servers()
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

    def UpdateShares(self, server, shares):
        diff = self.bitHopper.difficulty.get_difficulty()
        self.servers[server]['api_lag'] = False        
        prev_shares = self.servers[server]['shares']
        self.servers[server]['init'] = True
        if shares == prev_shares:
            time = .10*self.servers[server]['refresh_time']
            self.servers[server]['refresh_time'] += .10*self.servers[server]['refresh_time']
        else:
            self.servers[server]['refresh_time'] -= .10*self.servers[server]['refresh_time']
            time = self.servers[server]['refresh_time']

        if time <= self.servers[server]['refresh_limit']:
            time = self.servers[server]['refresh_limit']
        eventlet.spawn_after(time,self.update_api_server,server)

        try:
            k =  str('{0:d}'.format(int(shares)))
            ghash_duration = '  '
            if self.servers[server]['ghash'] > 0:
                ghash_duration += str('{0:.1f}gh/s '.format( self.servers[server]['ghash'] ))
            if self.servers[server]['duration'] > 0:
                ghash_duration += '\t' + str('{0:d}min.'.format( (self.servers[server]['duration']/60) ))
            k += '\t' + ghash_duration
        except Exception, e:
            self.bitHopper.log_dbg("Error formatting")
            self.bitHopper.log_dbg(e)
            k =  str(shares)

        #Display output to user when shares change
        if shares != prev_shares:
            if len(server) == 12:
                self.bitHopper.log_msg(str(server) +":"+ k)
            else:
                self.bitHopper.log_msg(str(server) +":\t"+ k)

        #If the shares indicate we found a block tell LP
        if shares < prev_shares and shares < 0.10 * diff:
            self.bitHopper.lp.set_owner(server)
        self.servers[server]['shares'] = shares
        self.servers[server]['err_api_count'] = 0
        api_disable_sec = 7200
        try:
            api_disable_sec = self.bitHopper.config.getint('main', 'api_disable_sec')
        except:
            pass
        if self.servers[server]['refresh_time'] > api_disable_sec and self.servers[server]['role'] not in ['info','backup','backup_latehop']:
            self.bitHopper.log_msg('Disabled due to unchanging api: ' + server)
            self.servers[server]['role'] = 'api_disable'
            return

    def errsharesResponse(self, error, server_name):
        self.bitHopper.log_msg(server_name + ' api error:' + str(error))
        pool = server_name
        self.servers[pool]['err_api_count'] += 1
        self.servers[pool]['init'] = True
        if self.servers[pool]['err_api_count'] > 1:
            self.servers[pool]['api_lag'] = True
        time = self.servers[pool]['refresh_time']
        if time < self.servers[pool]['refresh_limit']:
            time = self.servers[pool]['refresh_limit']
        eventlet.spawn_after(time, self.update_api_server, pool)

    def selectsharesResponse(self, response, server_name):
        #self.bitHopper.log_dbg('Calling sharesResponse for '+ args)
        server = self.servers[server_name]
        if server['role'] not in self.api_pull:
            return

        if server['api_method'] == 'json':
            try:
                info = json.loads(response)
            except ValueError, e:
                self.bitHopper.log_dbg(str(server_name) + " - unable to extract JSON from response")
                raise e
            for value in server['api_key'].split(','):
                info = info[value]
            if 'api_strip' in server:
                strip_char = server['api_strip'][1:-1]
                info = info.replace(strip_char,'')
                                          
            round_shares = int(info)
            if round_shares == None:
                round_shares = int(self.bitHopper.difficulty.get_difficulty())
            
            ghash = self.get_ghash(server, response, True)
            if ghash > 0:
                server['ghash'] = ghash
            if 'api_key_duration' in server:
                dur = json.loads(response)
                for value in server['api_key_duration'].split(','):
                    dur = dur[value]
                duration = self.get_duration(server, str(dur))
                if duration > 0:
                    server['duration'] = duration 
                    
            self.UpdateShares(server_name,round_shares)

        elif server['api_method'] == 'json_ec':
            try:
                info = json.loads(response[:response.find('}')+1])
            except ValueError, e:
                self.bitHopper.log_dbg(str(server_name) + " - unable to extract JSON from response")
                raise e
            for value in server['api_key'].split(','):
                info = info[value]
            round_shares = int(info)
            if round_shares == None:
                round_shares = int(self, self.bitHopper.difficulty.get_difficulty())
            self.UpdateShares(server_name,round_shares)

        elif server['api_method'] == 're':
            output = re.search(server['api_key'],response)
            if output == None:
                raise Exception(str(server_name) + " - unable to extract shares from response using regexp")
            if 'api_group' in server:
                output = output.group(int(server['api_group']))
            else:
                output = output.group(1)
            if 'api_index' in server:
                s,e = server['api_index'].split(',')
                s = int(s)
                if e == '0' or e =='':
                    output = output[s:]
                else:
                    output = output[s:int(e)]
            if 'api_strip' in server:
                strip_str = server['api_strip'][1:-1]
                output = output.replace(strip_str,'')
            round_shares = int(output)
            if round_shares == None:
                round_shares = int(self.bitHopper.difficulty.get_difficulty())
            self.UpdateShares(server_name,round_shares)
            
        elif server['api_method'] == 're_rateduration':
            # get hashrate and duration to estimate share
            server['isDurationEstimated'] = True
            ghash = self.get_ghash(server, response)
            if ghash < 0:
                ghash = 1
                                                            
            duration = self.get_duration(server, response)
            if duration < 0:
                duration = 7*24*3600
            
            old = server['last_pulled']
            server['last_pulled'] = time.time()
            diff = server['last_pulled'] - old
            
            server['duration_temporal'] = server['duration_temporal'] + diff
            
            # new round started or initial estimation
            rate = 0.25 * ghash
            if duration < server['duration'] or server['duration'] < 0: 
                round_shares = int(rate * duration)
            else:
                round_shares = server['shares'] + int(rate * diff)
            
            server['ghash'] = ghash
            server['duration'] = duration
            
            self.UpdateShares(server_name,round_shares)
        
        elif server['api_method'] == 're_shareestimate':
            # get share count based on user shares and user reward estimate
            output = re.search(server['api_key_shares'],response)
            shares = output.group(1)                
            
            output = re.search(server['api_key_estimate'],response)
            estimate = output.group(1)
            
            round_shares = int(50.0 * float(shares) / float(estimate))
            self.UpdateShares(server_name,round_shares)            
        
        elif server['api_method'] == 're_rate':
            output = re.search(server['api_key'],response)
            if 'api_group' in server:
                output = output.group(int(server['api_group']))
            else:
                output = output.group(1)
            if 'api_index' in server:
                s,e = server['api_index'].split(',')
                s = int(s)
                if e == '0' or e =='':
                    output = output[s:]
                else:
                    output = output[s:int(e)]
            if 'api_strip' in server:
                strip_str = server['api_strip'][1:-1]
                output = output.replace(strip_str,'')
            if 're_rate_type' in server:
                prefix = server['re_rate_type']
                if prefix == 'GH':
                    mult = 1000**3
                if prefix == 'MH':
                    mult = 1000**2
                if prefix == 'KH':
                    mult = 1000
                if prefix == 'None':
                    mult = 1
            else:
                mult = 1000**3
            rate = int(output)
            rate = rate * mult
            server['ghash'] = float(rate)/(1000**3) 
            rate = float(rate)/2**32
            old = server['last_pulled']
            server['last_pulled'] = time.time()
            diff = server['last_pulled'] - old
            shares = int(rate * diff)
            round_shares = shares + server['shares']
            self.UpdateShares(server_name ,round_shares)
        #Disable api scraping
        elif server['api_method'] == 'disable':
            self.UpdateShares(server_name,0)
            self.bitHopper.log_msg('Share estimation disabled for: ' + server['name'])
        else:
            self.bitHopper.log_msg('Unrecognized api method: ' + str(server))

        self.bitHopper.server_update()

    def get_ghash(self, server, response, is_json = False):
        if is_json == True:
            info = json.loads(response)
            if 'api_key_ghashrate' in server:
                for value in server['api_key_ghashrate'].split(','):
                    info = info[value]
                return float(info)
            if 'api_key_mhashrate' in server:
                for value in server['api_key_mhashrate'].split(','):
                    info = info[value]
                return float(info) / 1000.0
            if 'api_key_khashrate' in server:
                for value in server['api_key_khashrate'].split(','):
                    info = info[value]
                return float(info) / 1000000.0
            if 'api_key_hashrate' in server:
                for value in server['api_key_hashrate'].split(','):
                    info = info[value]
                return float(info) / 1000000000.0
            
        if 'api_key_ghashrate' in server:
            output = re.search(server['api_key_ghashrate'], response)
            return float(output.group(1).replace(' ', ''))
        if 'api_key_mhashrate' in server:
            output = re.search(server['api_key_mhashrate'], response)
            return float(output.group(1).replace(' ', '')) / 1000.0
        if 'api_key_khashrate' in server:
            output = re.search(server['api_key_khashrate'], response)
            return float(output.group(1).replace(' ', '')) / 1000000.0
        if 'api_key_hashrate' in server:
            output = re.search(server['api_key_hashrate'], response)
            return float(output.group(1).replace(' ', '')) / 1000000000.0
            
        return -1
    
    def get_duration(self, server, response):
        duration = -1 # I think this is not needed anymore? Could somebody double check?
        if 'api_key_duration_day_hour_min' in server:
            output = re.search(server['api_key_duration_day_hour_min'], response)
            try:
                day = int(output.group(1).replace(' ', ''))
            except AttributeError:
                day = 0
            try:
                hour = int(output.group(2).replace(' ', ''))
            except AttributeError:
                hour = 0
            try:
                minute = int(output.group(3).replace(' ', ''))
            except AttributeError:
                minute = 0
            if day == 0:
                if hour == 0:
                    if minute == 0:
                        duration = -1
                    else:
                        duration = minute * 60
                else:
                    duration = hour * 3600 + minute * 60
            else:
                duration = day*24*3600 + hour * 3600 + minute * 60
        elif 'api_key_duration_hour_min' in server:
            output = re.search(server['api_key_duration_hour_min'], response)
            try:
                hour = int(output.group(1).replace(' ', ''))
            except AttributeError:
                hour = 0
            try:
                minute = int(output.group(2).replace(' ', ''))
            except AttributeError:
                minute = 0
            if hour == 0:
                if minute == 0:
                    duration = -1
                else:
                    duration = minute * 60
            else:
                duration = hour * 3600 + minute * 60
        elif 'api_key_duration_min' in server:
            output = re.search(server['api_key_duration_min'], response)
            try:
                minute = int(output.group(1).replace(' ', ''))
            except AttributeError:
                minute = 0
            if minute == 0:
                duration = -1
            else:
                duration = minute * 60
        elif 'api_key_duration_sec' in server:
            output = re.search(server['api_key_duration_sec'], response)
            try:
                duration = int(output.group(1).replace(' ', ''))
            except AttributeError:
                duration = -1
        
        return duration

    def update_api_server(self,server):
        if self.servers[server]['role'] not in self.api_pull:
            return
        info = self.servers[server]
        self.bitHopper.scheduler.update_api_server(server)
        user_agent = None
        if 'user_agent' in info:
            user_agent = info['user_agent']
        value = self.bitHopper.work.get(info['api_address'], user_agent)
        try:
            self.selectsharesResponse( value, server)
        except Exception, e:
            self.errsharesResponse(e, server)

    def update_api_servers(self):
        for server in self.servers:
            eventlet.spawn_n(self.update_api_server, server)

if __name__ == "__main__":
    print 'Run python bitHopper.py instead.'
