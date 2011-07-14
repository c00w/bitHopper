#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import work
import json
from password import *
import bitHopper
from diff import difficulty

default_shares = difficulty

servers = {
        'bclc':{'shares':default_shares, 'name':'bitcoins.lc', 
            'mine_address':'bitcoins.lc:8080', 'user':bclc_user, 'pass':bclc_pass, 
            'lag':False, 'LP':None, 
            'api_address':'https://www.bitcoins.lc/stats.json', 'role':'info' },
        'mtred':{'shares':default_shares, 'name':'mtred',  
            'mine_address':'mtred.com:8337', 'user':mtred_user, 'pass':mtred_pass, 
            'lag':False, 'LP':None,
            'api_address':'https://mtred.com/api/user/key/d91c52cfe1609f161f28a1268a2915b8', 
            'role':'mine'},
        'btcg':{'shares':default_shares, 'name':'BTC Guild',  
            'mine_address':'us.btcguild.com:8332', 'user':btcguild_user, 
            'pass':btcguild_pass, 'lag':False, 'LP':None, 
            'api_address':'https://www.btcguild.com/pool_stats.php', 
            'user_api_address':'https://www.btcguild.com/api.php?api_key='+btcguild_user_apikey, 
            'role':'mine'},
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
             +'&action=poolstats', 'role':'mine'},
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

current_server = 'btcg'

def get_entry(server):
    global servers
    if server in servers:
        return servers[server]
    else:
        return None

def get_servers():
    global servers
    return servers

def get_current():
    global current_server
    return current_server

def set_current(server):
    global current_server
    current_server = server

def ozco_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['shares'])
    servers['ozco']['shares'] = round_shares
    bitHopper.log_msg('ozco.in:' + str(round_shares))

def mmf_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['shares_this_round'])
    servers['miningmainframe']['shares'] = round_shares
    bitHopper.log_msg( 'mining.mainframe.nl :' + str(round_shares))

def bitp_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['shares'])
    servers['bitp']['shares'] = round_shares
    bitHopper.log_msg( 'pool.bitp.it :' + str(round_shares))


def eclipsemc_sharesResponse(response):
    global servers
    info = json.loads(response[:response.find('}')+1])
    round_shares = int(info['round_shares'])
    servers['eclipsemc']['shares'] = round_shares
    bitHopper.log_msg( 'eclipsemc :' + str(round_shares))


def btcguild_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['round_shares'])
    servers['btcg']['shares'] = round_shares
    bitHopper.log_msg( 'btcguild :' + str(round_shares))

def bclc_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['round_shares'])
    servers['bclc']['shares'] = round_shares
    bitHopper.log_msg( 'bitcoin.lc :' + str(round_shares))
    
def mtred_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['server']['roundshares'])
    servers['mtred']['shares'] = round_shares
    bitHopper.log_msg('mtred :' + str(round_shares))

def mineco_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['shares_this_round'])
    servers['mineco']['shares'] = round_shares
    bitHopper.log_msg( 'mineco :' + str(round_shares))

def bitclockers_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['roundshares'])
    servers['bitclockers']['shares'] = round_shares
    bitHopper.log_msg( 'bitclockers :' + str(round_shares))

def errsharesResponse(error, args):
    bitHopper.log_msg('Error in pool api for ' + str(args))
    bitHopper.log_dbg(str(error))
    pool = args
    global servers
    servers[pool]['shares'] = 10**10

def selectsharesResponse(response, args):
    #bitHopper.log_dbg('Calling sharesResponse for '+ args)
    func_map= {'bitclockers':bitclockers_sharesResponse,
        'mineco':mineco_sharesResponse,
        'mtred':mtred_sharesResponse,
        'bclc':bclc_sharesResponse,
        'btcg':btcguild_sharesResponse,
        'eclipsemc':eclipsemc_sharesResponse,
        'miningmainframe':mmf_sharesResponse,
        'bitp':bitp_sharesResponse,
        'ozco':ozco_sharesResponse}
    func_map[args](response)
    bitHopper.server_update()

def update_api_servers():
    global servers
    for server in servers:
        info = servers[server]
        update = ['info','mine']
        if info['role'] in update:
            d = work.get(bitHopper.json_agent,info['api_address'])
            d.addCallback(selectsharesResponse, (server))
            d.addErrback(errsharesResponse, (server))
            d.addErrback(bitHopper.log_msg)

if __name__ == "__main__":
    print 'Run python bitHopper.py instead.'
