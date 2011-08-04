#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import work
import re
import ConfigParser
import os
import sys


class Pool():
    def __init__(self,bitHopper):
        self.servers = {}
        self.api_pull = ['mine','info','mine_slush','mine_nmc','mine_friendly','backup','backup_latehop']

        parser = ConfigParser.SafeConfigParser()
        try:
            # determine if application is a script file or frozen exe
            if hasattr(sys, 'frozen'):
                application_path = os.path.dirname(sys.executable)
            elif __file__:
                application_path = os.path.dirname(__file__)
            read = parser.read(os.path.join(application_path, 'user.cfg'))
        except:
            read = parser.read('user.cfg')
        if len(read) == 0:
            bitHopper.log_msg("user.cfg not found. You may need to move it from user.cfg.default")
            os._exit(1)
            
        userpools = parser.sections()

        try:
            # determine if application is a script file or frozen exe
            if hasattr(sys, 'frozen'):
                application_path = os.path.dirname(sys.executable)
            elif __file__:
                application_path = os.path.dirname(__file__)
            read = parser.read(os.path.join(application_path, 'pools.cfg'))
        except:
            read = parser.read('pools.cfg')
        if len(read) == 0:
            bitHopper.log_msg("pools.cfg not found.")
            os._exit(1)
            
        pools = parser.sections()
        for pool in userpools:
            self.servers[pool] = dict(parser.items(pool))

        if self.servers == {}:
            bitHopper.log_msg("No pools found in pools.cfg or user.cfg")
        self.current_server = pool
        
    def setup(self,bitHopper):
        self.bitHopper = bitHopper
        for server in self.servers:
            self.servers[server]['shares'] = int(bitHopper.difficulty.get_difficulty())
            self.servers[server]['lag'] = False
            self.servers[server]['api_lag'] = False
            self.servers[server]['refresh_time'] = 60
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
            
    def get_entry(self, server):
        if server in self.servers:
            return self.servers[server]
        else:
            return None

    def get_servers(self, ):
        return self.servers

    def get_current(self, ):
        return self.current_server

    def set_current(self, server):
        self.current_server = server

    def UpdateShares(self, server, shares):
        self.servers[server]['api_lag'] = False        
        prev_shares = self.servers[server]['shares']
        self.servers[server]['init'] = True
        if shares == prev_shares:
            time = .10*self.servers[server]['refresh_time']
            self.servers[server]['refresh_time'] += .10*self.servers[server]['refresh_time']
        else:
            self.servers[server]['refresh_time'] -= .10*self.servers[server]['refresh_time']
            time = self.servers[server]['refresh_time']

        if time <= 30:
            time = 30
        self.bitHopper.reactor.callLater(time,self.update_api_server,server)

        try:
            k =  str('{0:d}'.format(int(shares)))
        except Exception, e:
            self.bitHopper.log_dbg("Error formatting")
            self.bitHopper.log_dbg(e)
            k =  str(shares)
        if shares != prev_shares:
            self.bitHopper.log_msg(str(server) +": "+ k)
        self.servers[server]['shares'] = shares
        self.servers[server]['err_api_count'] = 0
        if self.servers[server]['refresh_time'] > 60*30 and self.servers[server]['role'] not in ['info','backup','backup_latehop']:
            self.bitHopper.log_msg('Disabled due to unchanging api: ' + server)
            self.servers[server]['role'] = 'api_disable'
            return

    def errsharesResponse(self, error, args):
        self.bitHopper.log_msg('Error in pool api for ' + str(args))
        self.bitHopper.log_dbg(str(error))
        pool = args
        self.servers[pool]['err_api_count'] += 1
        self.servers[pool]['init'] = True
        if self.servers[pool]['err_api_count'] > 1:
            self.servers[pool]['api_lag'] = True
        time = self.servers[pool]['refresh_time']
        self.bitHopper.reactor.callLater(time, self.update_api_server, pool)

    def selectsharesResponse(self, response, args):
        #self.bitHopper.log_dbg('Calling sharesResponse for '+ args)
        server = self.servers[args]
        if server['role'] not in self.api_pull:
            return

        if server['api_method'] == 'json':
            info = json.loads(response)
            for value in server['api_key'].split(','):
                info = info[value]
            if 'api_strip' in server:
                strip_char = server['api_strip'][1:-1]
                info = info.replace(strip_char,'')
            round_shares = int(info)
            if round_shares == None:
                round_shares = int(bitHopper.difficulty.get_difficulty())
            self.UpdateShares(args,round_shares)

        elif server['api_method'] == 'json_ec':
            info = json.loads(response[:response.find('}')+1])
            for value in server['api_key'].split(','):
                info = info[value]
            round_shares = int(info)
            if round_shares == None:
                round_shares = int(bitHopper.difficulty.get_difficulty())
            self.UpdateShares(args,round_shares)

        elif server['api_method'] == 're':
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
            round_shares = int(output)
            if round_shares == None:
                round_shares = int(bitHopper.difficulty.get_difficulty())
            self.UpdateShares(args,round_shares)
        else:
            self.bitHopper.log_msg('Unrecognized api method: ' + str(server))

        self.bitHopper.server_update()

    def update_api_server(self,server):
        if self.servers[server]['role'] not in self.api_pull:
            return
        info = self.servers[server]
        self.bitHopper.scheduler.update_api_server(server)
        d = work.get(self.bitHopper.json_agent,info['api_address'])
        d.addCallback(self.selectsharesResponse, (server))
        d.addErrback(self.errsharesResponse, (server))
        d.addErrback(self.bitHopper.log_msg)

    def update_api_servers(self, bitHopper):
        self.bitHopper = bitHopper
        for server in self.servers:
            info = self.servers[server]
            update = self.api_pull
            if info['role'] in update:
                d = work.get(self.bitHopper.json_agent,info['api_address'])
                d.addCallback(self.selectsharesResponse, (server))
                d.addErrback(self.errsharesResponse, (server))
                d.addErrback(self.bitHopper.log_msg)

if __name__ == "__main__":
    print 'Run python bitHopper.py instead.'
