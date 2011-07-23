#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import work
from password import *
import re
import ConfigParser

import htmllib 
def unescape(s):
    p = htmllib.HTMLParser(None)
    p.save_bgn()
    p.feed(s)
    return p.save_end()

class Pool():
    def __init__(self,bitHopper):
        self.servers = {}

        parser = ConfigParser.SafeConfigParser()
        parser.read('pool.cfg')
        pools = parser.sections()
        for pool in pools:
            self.servers[pool] = dict(parser.items(pool))
        self.current_server = 'mtred'
        
    def setup(self,bitHopper):
        self.bitHopper = bitHopper
        for server in self.servers:
            self.servers[server]['shares'] = bitHopper.difficulty.get_difficulty()
            self.servers[server]['lag'] = False
            self.servers[server]['refresh_time'] = 60
            self.servers[server]['rejects'] = self.bitHopper.db.get_rejects(server)
            self.servers[server]['user_shares'] = self.bitHopper.db.get_shares(server)
            self.servers[server]['payout'] = self.bitHopper.db.get_payout(server)
            if 'api_address' not in self.servers[server]:
                self.servers[server]['api_address'] = server
            if 'name' not in self.servers[server]:
                self.server[server]['name'] = server
            
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

        prev_shares = self.servers[server]['shares']
        if shares == prev_shares:
            time = .10*self.servers[server]['refresh_time']
            if time <= 10:
                time = 10.
            self.servers[server]['refresh_time'] += .10*self.servers[server]['refresh_time']
            self.bitHopper.reactor.callLater(time,self.update_api_server,server)
        else:
            self.servers[server]['refresh_time'] -= .10*self.servers[server]['refresh_time']
            time = self.servers[server]['refresh_time']
            if time <= 10:
                self.servers[server]['refresh_time'] = 10
            self.bitHopper.reactor.callLater(time,self.update_api_server,server)

        try:
            k =  str('{0:,d}'.format(int(shares)))
        except Exception, e:
            self.bitHopper.log_dbg("Error formatting")
            self.bitHopper.log_dbg(e)
            k =  str(shares)
        if shares != prev_shares:
            self.bitHopper.log_msg(str(server) +": "+ k)
        self.servers[server]['shares'] = shares
        if self.servers[server]['refresh_time'] > 60*30:
            self.bitHopper.log_msg('Disabled due to unchanging api: ' + server)
            self.servers[server]['role'] = 'api_disable'
            return

    def errsharesResponse(self, error, args):
        self.bitHopper.log_msg('Error in pool api for ' + str(args))
        self.bitHopper.log_dbg(str(error))
        pool = args
        self.servers[pool]['shares'] = 10**10
        time = self.servers[pool]['refresh_time']
        self.bitHopper.reactor.callLater(time, self.update_api_server, pool)

    def selectsharesResponse(self, response, args):
        self.bitHopper.log_dbg('Calling sharesResponse for '+ args)
        server = self.servers[args]
        if server['role'] not in ['mine','info']:
            return

        if server['api_method'] == 'json':
            info = json.loads(response)
            for value in server['api_key'].split(','):
                info = info[value]
            round_shares = int(info)
            self.UpdateShares(args,round_shares)

        elif server['api_method'] == 'json_ec':
            info = json.loads(response[:response.find('}')+1])
            for value in server['api_key'].split(','):
                info = info[value]
            round_shares = int(info)
            self.UpdateShares(args,round_shares)

        elif server['api_method'] == 're':
            output = re.search(server['api_key'],response)
            output = output.group(0)
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
            self.UpdateShares(args,round_shares)
        else:
            self.bitHopper.log_msg('Unrecognized api method: ' + str(server))

        self.bitHopper.server_update()

    def update_api_server(self,server):
        if self.servers[server]['role'] not in ['mine','info']:
            return
        info = self.servers[server]
        d = work.get(self.bitHopper.json_agent,info['api_address'])
        d.addCallback(self.selectsharesResponse, (server))
        d.addErrback(self.errsharesResponse, (server))
        d.addErrback(self.bitHopper.log_msg)

    def update_api_servers(self, bitHopper):
        self.bitHopper = bitHopper
        for server in self.servers:
            info = self.servers[server]
            update = ['info','mine']
            if info['role'] in update:
                d = work.get(self.bitHopper.json_agent,info['api_address'])
                d.addCallback(self.selectsharesResponse, (server))
                d.addErrback(self.errsharesResponse, (server))
                d.addErrback(self.bitHopper.log_msg)

if __name__ == "__main__":
    print 'Run python bitHopper.py instead.'
