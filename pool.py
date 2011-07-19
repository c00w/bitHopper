#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import work
from password import *
from diff import difficulty
import re

class Pool():
    def __init__(self):
        default_shares = difficulty
        
        self.servers = {
                'bclc':{'shares':default_shares, 'name':'bitcoins.lc', 
                    'mine_address':'bitcoins.lc:8080', 'user':bclc_user, 'pass':bclc_pass, 
                    'lag':False, 'LP':None, 
                    'api_address':'https://www.bitcoins.lc/stats.json', 'role':'disable' },
                'mtred':{'shares':default_shares, 'name':'mtred',  
                    'mine_address':'mtred.com:8337', 'user':mtred_user, 'pass':mtred_pass, 
                    'lag':False, 'LP':None,
                    'api_address':'https://mtred.com/api/user/key/' + mtred_user_apikey, 
                    'role':'mine'},
                'btcg':{'shares':default_shares, 'name':'BTC Guild',  
                    'mine_address':'us.btcguild.com:8332', 'user':btcguild_user, 
                    'pass':btcguild_pass, 'lag':False, 'LP':None, 
                    'api_address':'https://www.btcguild.com/pool_stats.php', 
                    'user_api_address':'https://www.btcguild.com/api.php?api_key='+btcguild_user_apikey, 
                    'role':'disable'},
                'eligius':{'shares':difficulty*.41, 'name':'eligius', 
                    'mine_address':'su.mining.eligius.st:8337', 'user':eligius_address, 
                    'pass':'x', 'lag':False, 'LP':None, 'role':'backup'},
                'arsbitcoin':{'shares':difficulty*.41, 'name':'arsbitcoin',
                    'mine_address':'arsbitcoin.com:8344', 'user':ars_user, 
                    'pass':ars_pass, 'lag':False, 'LP':None, 'role':'backup'},
                'mineco':{'shares': default_shares, 'name': 'mineco.in',
                    'mine_address': 'mineco.in:3000', 'user': mineco_user,
                    'pass': mineco_pass, 'lag': False, 'LP': None,
                    'api_address':'https://mineco.in/stats.json', 'role':'disable'},
                'bitclockers':{'shares': default_shares, 'name': 'bitclockers.com',
                    'mine_address': 'pool.bitclockers.com:8332', 'user': bitclockers_user,
                    'pass': bitclockers_pass, 'lag': False, 'LP': None,
                    'api_address':'https://bitclockers.com/api', 'role':'disable',
                    'user_api_address':'https://bitclockers.com/api/'+bitclockers_user_apikey},
               'eclipsemc':{'shares': default_shares, 'name': 'eclipsemc.com',
                    'mine_address': 'pacrim.eclipsemc.com:8337', 'user': eclipsemc_user,
                    'pass': eclipsemc_pass, 'lag': False, 'LP': None,
                    'api_address':'https://eclipsemc.com/api.php?key='+ eclipsemc_apikey
                     +'&action=poolstats', 'role':'disable'},
                'miningmainframe':{'shares': default_shares, 'name': 'mining.mainframe.nl',
                   'mine_address': 'mining.mainframe.nl:8343', 'user': miningmainframe_user,
                   'pass': miningmainframe_pass, 'lag': False, 'LP': None,
                    'api_address':'http://mining.mainframe.nl/api', 'role':'disable'},
                'bitp':{'shares': default_shares, 'name': 'bitp.it',
                   'mine_address': 'pool.bitp.it:8334', 'user': bitp_user,
                   'pass': bitp_pass, 'lag': False,
                   'api_address':'https://pool.bitp.it/leaderboard', 'role':'disable',
                   'user_api_address':'https://pool.bitp.it/api/user?token=' + bitp_user_apikey},
                'ozco':{'shares': default_shares, 'name': 'ozco.in',
                   'mine_address': 'ozco.in:8332', 'user': ozco_user,
                   'pass': ozco_pass, 'lag': False,
                   'api_address':'https://ozco.in/api.php', 'role':'mine'},
               'triple':{'shares': default_shares, 'name': 'triplemining.com',
                   'mine_address': 'eu1.triplemining.com:8344', 'user': triple_user,
                   'pass': triple_pass, 'lag': False,
                   'api_address':'https://www.triplemining.com/stats',  
                    'role':'mine'},
                'x8s':{'shares': default_shares, 'name': 'btc.x8s.de',
                    'mine_address': 'pit.x8s.de:8337', 'user': x8s_user,
                    'pass': x8s_pass, 'lag': False, 'LP': None,
                    'api_address':'', 
                    'role':'disable'},   
                'rfc':{'shares': default_shares, 'name': 'rfcpool.com',
                    'mine_address': 'pool.rfcpool.com:8332', 'user': rfc_user,
                    'pass': 'x', 'lag': False, 'LP': None,
                    'api_address':'https://www.rfcpool.com/api/pool/stats', 
                    'role':'mine'},  
                }

        self.current_server = 'mtred'

        
    def setup(self,bitHopper):
        self.bitHopper = bitHopper
        for server in self.servers:
            self.servers[server]['refresh_time'] = 60
            self.servers[server]['rejects'] = self.bitHopper.db.get_rejects(server)
            self.servers[server]['user_shares']=self.bitHopper.db.get_shares(server)

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
            k =  str('{0:,d}'.format(shares))
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


    def rfc_sharesResponse(self, response):
        round_shares = json.loads(response)['poolstats']['round_shares']
        self.UpdateShares('rfc',round_shares)

    def triple_sharesResponse(self, response):
        output = re.search('<td>\d+</td>', response)
        match = output.group(0)
        match = match[4:-5]
        round_shares = int(match)
        self.UpdateShares('triple',round_shares)

    def ozco_sharesResponse(self, response):
        info = json.loads(response)
        round_shares = int(info['shares'])
        self.UpdateShares('ozco',round_shares)

    def mmf_sharesResponse(self, response):
        info = json.loads(response)
        round_shares = int(info['shares_this_round'])
        self.UpdateShares('miningmainframe',round_shares)

    def bitp_sharesResponse(self, response):
        output = re.search('Total</b></td>\n        <td>\d+', response)
        match = output.group(0)
        match = match[match.find('<td>')+4:]
        round_shares = int(match)
        self.UpdateShares('bitp',round_shares)

    def eclipsemc_sharesResponse(self, response):
        info = json.loads(response[:response.find('}')+1])
        round_shares = int(info['round_shares'])
        self.UpdateShares('eclipsemc',round_shares)

    def btcguild_sharesResponse(self, response):
        info = json.loads(response)
        round_shares = int(info['round_shares'])
        self.UpdateShares('btcg',round_shares)

    def bclc_sharesResponse(self, response):
        info = json.loads(response)
        round_shares = int(info['round_shares'])
        self.UpdateShares('bclc',round_shares)
        
    def mtred_sharesResponse(self, response):
        info = json.loads(response)
        round_shares = int(info['server']['roundshares'])
        self.UpdateShares('mtred',round_shares)

    def mineco_sharesResponse(self, response):
        info = json.loads(response)
        round_shares = int(info['shares_this_round'])
        self.UpdateShares('mineco',round_shares)

    def bitclockers_sharesResponse(self, response):
        info = json.loads(response)
        round_shares = int(info['roundshares'])
        self.UpdateShares('bitclockers',round_shares)

    def errsharesResponse(self, error, args):
        self.bitHopper.log_msg('Error in pool api for ' + str(args))
        self.bitHopper.log_dbg(str(error))
        pool = args
        self.servers[pool]['shares'] = 10**10
        time = self.servers[pool]['refresh_time']
        self.bitHopper.reactor.callLater(time, self.update_api_server, pool)

    def selectsharesResponse(self, response, args):
        self.bitHopper.log_dbg('Calling sharesResponse for '+ args)
        func_map= {'bitclockers':self.bitclockers_sharesResponse,
            'mineco':self.mineco_sharesResponse,
            'mtred':self.mtred_sharesResponse,
            'bclc':self.bclc_sharesResponse,
           #'btcg':self.btcguild_sharesResponse,
            'eclipsemc':self.eclipsemc_sharesResponse,
            'miningmainframe':self.mmf_sharesResponse,
            'bitp':self.bitp_sharesResponse,
            'ozco':self.ozco_sharesResponse,
            'triple':self.triple_sharesResponse,
            'rfc':self.rfc_sharesResponse}
        func_map[args](response)
        self.bitHopper.server_update()

    def update_api_server(self,server):
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
