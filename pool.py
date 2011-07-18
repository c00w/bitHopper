#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import work
import json
from password import *
from diff import difficulty

class Pool():
    def __init__(self):
        default_shares = difficulty

        self.servers = {
                'bclc':{'shares':default_shares, 'name':'bitcoins.lc', 
                    'mine_address':'bitcoins.lc:8080', 'user':bclc_user, 'pass':bclc_pass, 
                    'lag':False, 'LP':None, 
                    'api_address':'https://www.bitcoins.lc/stats.json', 'role':'info' },
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
                    'role':'info'},
                'eligius':{'shares':difficulty*.41, 'name':'eligius', 
                    'mine_address':'su.mining.eligius.st:8337', 'user':eligius_address, 
                    'pass':'x', 'lag':False, 'LP':None, 'role':'backup'},
                'arsbitcoin':{'shares':difficulty*.41, 'name':'arsbitcoin',
                    'mine_address':'arsbitcoin.com:8344', 'user':ars_user, 
                    'pass':ars_pass, 'lag':False, 'LP':None, 'role':'backup'},
                'mineco':{'shares': default_shares, 'name': 'mineco.in',
                    'mine_address': 'mineco.in:3000', 'user': mineco_user,
                    'pass': mineco_pass, 'lag': False, 'LP': None,
                    'api_address':'https://mineco.in/stats.json', 'role':'info'},
                'bitclockers':{'shares': default_shares, 'name': 'bitclockers.com',
                    'mine_address': 'pool.bitclockers.com:8332', 'user': bitclockers_user,
                    'pass': bitclockers_pass, 'lag': False, 'LP': None,
                    'api_address':'https://bitclockers.com/api', 'role':'info',
                    'user_api_address':'https://bitclockers.com/api/'+bitclockers_user_apikey},
               'eclipsemc':{'shares': default_shares, 'name': 'eclipsemc.com',
                    'mine_address': 'pacrim.eclipsemc.com:8337', 'user': eclipsemc_user,
                    'pass': eclipsemc_pass, 'lag': False, 'LP': None,
                    'api_address':'https://eclipsemc.com/api.php?key='+ eclipsemc_apikey
                     +'&action=poolstats', 'role':'info'},
                'miningmainframe':{'shares': default_shares, 'name': 'mining.mainframe.nl',
                   'mine_address': 'mining.mainframe.nl:8343', 'user': miningmainframe_user,
                   'pass': miningmainframe_pass, 'lag': False, 'LP': None,
                    'api_address':'http://mining.mainframe.nl/api', 'role':'info'},
                'bitp':{'shares': default_shares, 'name': 'bitp.it',
                   'mine_address': 'pool.bitp.it:8334', 'user': bitp_user,
                   'pass': bitp_pass, 'lag': False, 'LP': None,
                   'api_address':'https://pool.bitp.it/api/pool', 'role':'mine',
                   'user_api_address':'https://pool.bitp.it/api/user?token=' + bitp_user_apikey},
                'ozco':{'shares': default_shares, 'name': 'ozco.in',
                   'mine_address': 'ozco.in:8332', 'user': ozco_user,
                   'pass': ozco_pass, 'lag': False, 'LP': None,
                   'api_address':'https://ozco.in/api.php', 'role':'mine'}
                }

        self.current_server = 'mtred'

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
        try:
            k =  str('{0:,d}'.format(shares))
        except Exception, e:
            #bitHopper.log_dbg("Error formatting")
            #bitHopper.log_dbg(e)
            k =  str(shares)
        self.bitHopper.log_msg(str(server) +": "+ k)
        self.servers[server]['shares'] = shares

    def ozco_sharesResponse(self, response):
        info = json.loads(response)
        round_shares = int(info['shares'])
        self.UpdateShares('ozco',round_shares)

    def mmf_sharesResponse(self, response):
        info = json.loads(response)
        round_shares = int(info['shares_this_round'])
        self.UpdateShares('miningmainframe',round_shares)

    def bitp_sharesResponse(self, response):
        info = json.loads(response)
        round_shares = int(info['shares'])
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
            'ozco':self.ozco_sharesResponse}
        func_map[args](response)
        self.bitHopper.server_update()

    def update_api_servers(self, bitHopper):
        self.bitHopper = bitHopper
        global servers
        for server in self.servers:
            info = self.servers[server]
            update = ['info','mine']
            if info['role'] in update:
                d = work.get(bitHopper.json_agent,info['api_address'])
                d.addCallback(self.selectsharesResponse, (server))
                d.addErrback(self.errsharesResponse, (server))
                d.addErrback(self.bitHopper.log_msg)

if __name__ == "__main__":
    print 'Run python bitHopper.py instead.'
