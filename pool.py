#!/bin/env python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import work
import sys
import exceptions
import optparse
import time

from twisted.web import server, resource
from client import Agent
from _newclient import Request
from twisted.internet import reactor, defer
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
from twisted.python import log, failure

import urllib2

from password import *

def get_difficulty():
    req = urllib2.Request('http://blockexplorer.com/q/getdifficulty')
    response = urllib2.urlopen(req)
    diff_string = response.read()
    return float(diff_string)

difficulty = get_difficulty()

default_shares = difficulty

servers = {
        'bclc':{'shares':default_shares, 'name':'bitcoins.lc', 
            'mine_address':'bitcoins.lc:8080', 'user':bclc_user, 'pass':bclc_pass, 
            'lag':False, 'LP':None, 
            'api_address':'https://www.bitcoins.lc/stats.json' },
        'mtred':{'shares':default_shares, 'name':'mtred',  
            'mine_address':'mtred.com:8337', 'user':mtred_user, 'pass':mtred_pass, 
            'lag':False, 'LP':None,
            'api_address':'https://mtred.com/api/user/key/d91c52cfe1609f161f28a1268a2915b8'},
        'btcg':{'shares':default_shares, 'name':'BTC Guild',  
            'mine_address':'us.btcguild.com:8332', 'user':btcguild_user, 
            'pass':btcguild_pass, 'lag':False, 'LP':None, 
            'api_address':'https://www.btcguild.com/pool_stats.php'},
        'eligius':{'shares':difficulty*.41, 'name':'eligius', 
            'mine_address':'su.mining.eligius.st:8337', 'user':eligius_address, 
            'pass':'x', 'lag':False, 'LP':None},
        'mineco':{'shares': default_shares, 'name': 'mineco.in',
            'mine_address': 'mineco.in:3000', 'user': mineco_user,
            'pass': mineco_pass, 'lag': False, 'LP': None,
            'api_address':'https://mineco.in/stats.json', 'info':''},
        'bitclockers':{'shares': default_shares, 'name': 'bitclockers.com',
            'mine_address': 'pool.bitclockers.com:8332', 'user': bitclockers_user,
            'pass': bitclockers_pass, 'lag': False, 'LP': None,
            'api_address':'https://bitclockers.com/api'},
       'eclipsemc':{'shares': default_shares, 'name': 'eclipsemc.com',
            'mine_address': 'pacrim.eclipsemc.com:8337', 'user': eclipsemc_user,
            'pass': eclipsemc_pass, 'lag': False, 'LP': None,
            'api_address':'https://eclipsemc.com/api.php?key='+ eclipsemc_apikey
             +'&action=poolstats'},
        'miningmainframe':{'shares': default_shares, 'name': 'mining.mainframe.nl',
           'mine_address': 'mining.mainframe.nl:8343', 'user': miningmainframe_user,
           'pass': miningmainframe_pass, 'lag': False, 'LP': None,
            'api_address':'http://mining.mainframe.nl/api'},
        'bitp':{'shares': default_shares, 'name': 'bitp.it',
           'mine_address': 'pool.bitp.it:8334', 'user': bitp_user,
           'pass': bitp_pass, 'lag': False, 'LP': None,
            'api_address':'https://pool.bitp.it/api/pool', 'info':''}
        }

current_server = 'btcg'
json_agent = Agent(reactor)
lp_agent = Agent(reactor, persistent=True)
new_server = Deferred()

lp_set = False
options = None

def log_msg(msg):
    if options == None:
        print time.strftime("[%H:%M:%S] ") +str(msg)
        return
    if options.debug == True:
        log.msg(msg)
        return
    print time.strftime("[%H:%M:%S] ") +str(msg)

def log_dbg(msg):
    if options == None:
        return
    if options.debug == True:
        log.err(msg)
        return
    return

@defer.inlineCallbacks
def update_lp(response):
    global current_server
    log_msg("LP triggered from server " + str(current_server))
    global lp_set
    global new_server

    finish = Deferred()
    response.deliverBody(work.WorkProtocol(finish))
    try:
        body = yield finish
    except ResponseFailed:
        log_dbg('Reading LP Response failed')
        lp_set = True
        return

    try:
        message = json.loads(body)
        value =  message['result']
        #defer.returnValue(value)
    except exceptions.ValueError, e:
        log_dbg("Error in json decoding, Probably not a real LP response")
        lp_set = True
        log_dbg(body)
        defer.returnValue(None)

    update_servers()
    current = current_server
    select_best_server()
    if current == current_server:
        lp_set = False      
        log_msg("LP triggering clients manually")
        new_server.callback(None)
        new_server = Deferred()
        
    defer.returnValue(None)

def set_lp(url, check = False):
    global lp_set
    if check:
        return not lp_set

    if lp_set:
        return

    global json_agent
    global servers
    global current_server
    server = servers[current_server]
    if url[0] == '/':
        lp_address = str(server['mine_address']) + str(url)
    else:
        lp_address = str(url)
    log_msg("LP Call " + lp_address)
    lp_set = True
    work.jsonrpc_lpcall(json_agent,server, lp_address, update_lp)


def select_best_server():
    """selects the best server for pool hopping. If there is not good server it returns eligious"""
    global servers
    global access
    global current_server
    global difficulty
    server_name = None

    min_shares = difficulty*.40
    
    for server in servers:
        info = servers[server]
        if 'info' in info:
            continue
        if info['shares']< min_shares and info['lag'] == False:
            min_shares = servers[server]['shares']
            server_name = server

    if server_name == None  and servers['eligius']['lag'] == False:
        server_name = 'eligius'

    elif server_name == None:
        min_shares = 10**10
        for server in servers:
            info = servers[server]
            if 'info' in info:
                continue
            if info['shares']< min_shares and info['lag'] == False:
                min_shares = servers[server]['shares']
                server_name = server

    if server_name == None:
        server_name = 'eligius'

    global new_server
    global lp_set

    if current_server != server_name:
        current_server = server_name
        lp_set = False
        log_msg("Server change to " + str(current_server) + ", telling client with LP")
        new_server.callback(None)
        new_server = Deferred()
        
    return

def get_new_server(server):
    global servers
    global current_server
    servers[current_server]['lag'] = True
    select_best_server()
    return servers[current_server]

def server_update():
    global servers
    min_shares = 10**10
    if servers[current_server]['shares'] > difficulty * .10:
        for server in servers:
            if servers[server]['shares'] < min_shares:
                min_shares = servers[server]['shares']

        if min_shares < servers[current_server]['shares']/2:
            select_best_server()
            return

    if servers[current_server]['shares'] > difficulty * .40:
        select_best_server()
        return
def mmf_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['shares_this_round'])
    servers['miningmainframe']['shares'] = round_shares
    log_msg( 'mining.mainframe.nl :' + str(round_shares))

def bitp_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['shares'])
    servers['bitp']['shares'] = round_shares
    log_msg( 'pool.bitp.nl :' + str(round_shares))


def eclipsemc_sharesResponse(response):
    global servers
    info = json.loads(response[:response.find('}')+1])
    round_shares = int(info['round_shares'])
    servers['eclipsemc']['shares'] = round_shares
    log_msg( 'eclipsemc :' + str(round_shares))


def btcguild_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['round_shares'])
    servers['btcg']['shares'] = round_shares
    log_msg( 'btcguild :' + str(round_shares))

def bclc_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['round_shares'])
    servers['bclc']['shares'] = round_shares
    log_msg( 'bitcoin.lc :' + str(round_shares))
    
def mtred_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['server']['roundshares'])
    servers['mtred']['shares'] = round_shares
    log_msg('mtred :' + str(round_shares))


def mineco_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['shares_this_round'])
    servers['mineco']['shares'] = round_shares
    log_msg( 'mineco :' + str(round_shares))

def bitclockers_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['roundshares'])
    servers['bitclockers']['shares'] = round_shares
    log_msg( 'bitclockers :' + str(round_shares))

def errsharesResponse(error, args):
    log_msg('Error in pool api for ' + str(args))
    log_msg(str(error))
    pool = args
    global servers
    servers[pool]['shares'] = 10**10

def selectsharesResponse(response, args):
    #log_dbg('Calling sharesResponse for '+ args)
    func_map= {'bitclockers':bitclockers_sharesResponse,
        'mineco':mineco_sharesResponse,
        'mtred':mtred_sharesResponse,
        'bclc':bclc_sharesResponse,
        'btcg':btcguild_sharesResponse,
        'eclipsemc':eclipsemc_sharesResponse,
        'miningmainframe':mmf_sharesResponse,
        'bitp':bitp_sharesResponse}
    func_map[args](response)
    server_update()

def update_servers():
    global servers
    for server in servers:
        global json_agent
        if server is not 'eligius':
            info = servers[server]
            d = work.get(json_agent,info['api_address'])
            d.addCallback(selectsharesResponse, (server))
            d.addErrback(errsharesResponse, (server))
            d.addErrback(log_msg)

@defer.inlineCallbacks
def delag_server():
    log_dbg('Running Delager')
    global servers
    global json_agent
    for index in servers:
        server = servers[index]
        if server['lag'] == True:
            data = yield work.jsonrpc_call(json_agent, server,[], set_lp)
            if data != None:
                server['lag'] = False
    

def bitHopper_Post(request):
   
    global options
    if not options.noLP:
        request.setHeader('X-Long-Polling', '/LP')
    rpc_request = json.loads(request.content.read())
    #check if they are sending a valid message
    if rpc_request['method'] != "getwork":
        return json.dumps({'result':None, 'error':'Not supported', 'id':rpc_request['id']})


    #Check for data to be validated
    global servers
    global current_server
    global json_agent
    pool_server=servers[current_server]
    
    data = rpc_request['params']
    j_id = rpc_request['id']

    log_msg('RPC request ' + str(data) + " submitted to " + str(pool_server['name']))
    work.jsonrpc_getwork(json_agent, pool_server, data, j_id, request, get_new_server, set_lp)

    return server.NOT_DONE_YET

def bitHopperLP(value, *methodArgs):
    try:
        log_msg('LP triggered serving miner')
        request = methodArgs[0]
        #Duplicated from above because its a little less of a hack
        #But apparently people expect well formed json-rpc back but won't actually make the call 
        try:
            json_request = request.content.read()
        except Exception,e:
            log_dbg( 'reading request content failed')
            json_request = None
        try:
            rpc_request = json.loads(json_request)
        except Exception, e:
            log_dbg('Loading the request failed')
            rpc_request = {'params':[],'id':1}
        #Check for data to be validated
        global servers
        global current_server
        global json_agent
        pool_server=servers[current_server]
        
        data = rpc_request['params']
        j_id = rpc_request['id']

        work.jsonrpc_getwork(json_agent, pool_server, data, j_id, request, get_new_server, set_lp)

    except Exception, e:
        log_msg('Error Caught in bitHopperLP')
        log_dbg(str(e))
        try:
            request.finish()
        except Exception, e:
            log_dbg( "Client already disconnected Urgh.")

    return None

class lpSite(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        global new_server
        new_server.addCallback(bitHopperLP, (request))
        return server.NOT_DONE_YET

    def render_POST(self, request):
        global new_server
        new_server.addCallback(bitHopperLP, (request))
        return server.NOT_DONE_YET


    def getChild(self,name,request):
        return self

class bitSite(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        global new_server
        new_server.addCallback(bitHopperLP, (request))
        return server.NOT_DONE_YET

    def render_POST(self, request):
        return bitHopper_Post(request)


    def getChild(self,name,request):
        if name == 'LP':
            return lpSite()
        return self

def main():
    global options
    parser = optparse.OptionParser(description='bitHopper')
    parser.add_option('--noLP', action = 'store_true' ,default=False, help='turns off client side longpolling')
    parser.add_option('--debug', action= 'store_true', default = False, help='Use twisted output')
    args, rest = parser.parse_args()
    options = args

    if options.debug: log.startLogging(sys.stdout)
    site = server.Site(bitSite())
    reactor.listenTCP(8337, site)
    update_call = LoopingCall(update_servers)
    update_call.start(117)
    delag_call = LoopingCall(delag_server)
    delag_call.start(30)
    reactor.run()

if __name__ == "__main__":
    main()

