#!/bin/python2.7
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import time
from jsonrpc import ServiceProxy
import socket
import os
import base64
import work
import sys
import exceptions

from zope.interface import implements

from twisted.web import server, resource
from twisted.web.client import getPage, Agent
from twisted.web.iweb import IBodyProducer
from twisted.web.http_headers import Headers
from twisted.internet import reactor, threads, defer
from twisted.internet.defer import succeed, Deferred
from twisted.internet.task import LoopingCall
import urllib2
from twisted.internet.protocol import Protocol
from twisted.python import log

#SET THESE
bclc_user  = "FSkyvM"
bclc_pass = "xndzEU"
mtred_user = 'scarium'
mtred_pass = 'x'
eligius_address = '1AofHmwVef5QkamCW6KqiD4cRqEcq5U7hZ'
btcguild_user = 'c00w_test'
btcguild_pass = 'x'
bitclockers_user = 'flargle'
bitclockers_pass = 'x'
mineco_user = 'c00w.test'
mineco_pass = 'x'
#REALLY

def get_difficulty():
    req = urllib2.Request('http://blockexplorer.com/q/getdifficulty')
    response = urllib2.urlopen(req)
    diff_string = response.read()
    return float(diff_string)

difficulty = get_difficulty()

default_shares = difficulty

servers = {
        'bclc':{'time':time.time(), 'shares':default_shares, 'name':'bitcoins.lc', 
            'mine_address':'bitcoins.lc:8080', 'user':bclc_user, 'pass':bclc_pass, 
            'lag':False, 'LP':None},
        'mtred':{'time':time.time(), 'shares':default_shares, 'name':'mtred',  
            'mine_address':'mtred.com:8337', 'user':mtred_user, 'pass':mtred_pass, 
            'lag':False, 'LP':None},
        'btcg':{'time':time.time(), 'shares':default_shares, 'name':'BTC Guild',  
            'mine_address':'uscentral.btcguild.com:8332', 'user':btcguild_user, 
            'pass':btcguild_pass, 'lag':False, 'LP':None},
        'eligius':{'time':time.time(), 'shares':difficulty*.41, 'name':'eligius', 
            'mine_address':'mining.eligius.st:8337', 'user':eligius_address, 
            'pass':'x', 'lag':False, 'LP':None},
        'mineco':{'time': time.time(), 'shares': default_shares, 'name': 'mineco.in',
            'mine_address': 'mineco.in:3000', 'user': mineco_user,
            'pass': mineco_pass, 'lag': False, 'LP': None},
        'bitclockers':{'time': time.time(), 'shares': 0, 'name': 'bitclockers.com',
            'mine_address': 'pool.bitclockers.com:8332', 'user': bitclockers_user,
            'pass': bitclockers_pass, 'lag': False, 'LP': None}
        }

current_server = 'eligius'
json_agent = Agent(reactor)
new_server = Deferred()

lp_set = True

def update_lp(body):
    return
    global current_server
    log.msg("LP triggered from server " + str(current_server))
    global lp_set
    global new_server
    lp_set = False
    update_servers()
    current = current_server
    select_best_server()
    if current == current_server:
        log.msg("LP triggering clients manually")
        new_server.callback(None)
    return None

def set_lp(url, check = False):
    return
    global lp_set
    if check:
        return not lp_set

    if lp_set:
        return

    log.err('LP IS DISABLED BUT SOMEHOW IT JUST EXECUTED')
    global json_agent
    global servers
    global current_server
    server = servers[current_server]
    log.msg("LP Call " + str(server['mine_address']) + str(url))
    lp_set = True
    work.jsonrpc_lpcall(json_agent,server, url, update_lp)


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
        log.msg("LP Triggering clients on server change")
        new_server.callback(None)
        
    return

def get_new_server(server):
    global servers
    global current_server
    server['lag'] = True
    select_best_server()
    return servers[current_server]

def server_update():
    global servers
    min_shares = 10**10
    if servers[current_server]['shares'] > difficulty * .10:
        for server in servers:
            if servers[server]['shares'] < min_shares:
                min_shares = servers[server]['shares']

        if min_shares < servers[current_server]['shares']:
            if servers[current_server]['shares'] - min_shares > .50 * servers[current_server]['shares']:
                select_best_server()
                return

    if servers[current_server]['shares'] > difficulty * .40:
        select_best_server()
        return

def btcguild_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['round_shares'])
    servers['btcg']['shares'] = round_shares
    log.msg( 'btcguild :' + str(round_shares))

def bclc_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['round_shares'])
    servers['bclc']['shares'] = round_shares
    log.msg( 'bitcoin.lc :' + str(round_shares))
    server_update()
    
def mtred_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['server']['servers']['n0']['roundshares'])
    servers['mtred']['shares'] = round_shares
    log.msg('mtred :' + str(round_shares))
    server_update()


def mineco_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['shares_this_round'])
    servers['mineco']['shares'] = round_shares
    log.msg( 'mineco :' + str(round_shares))
    server_update()

def bitclockers_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['roundshares'])
    servers['bitclockers']['shares'] = round_shares
    log.msg( 'bitclockers :' + str(round_shares))
    server_update()

def errsharesResponse(error, args):
    log.msg('Error in pool api for ' + str(args))
    pool = args
    global servers
    servers[pool]['shares'] = 10**10

def btcg_getshares():
    d = getPage('https://www.btcguild.com/pool_stats.php')
    d.addCallback(bclc_sharesResponse)
    d.addErrback(errsharesResponse, ('btcg'))
    d.addErrback(log.err)

def bclc_getshares():
    d = getPage('https://www.bitcoins.lc/stats.json')
    d.addCallback(bclc_sharesResponse)
    d.addErrback(errsharesResponse, ('bclc'))
    d.addErrback(log.err)

def mtred_getshares():
    d = getPage('https://mtred.com/api/user/key/d91c52cfe1609f161f28a1268a2915b8')
    d.addCallback( mtred_sharesResponse )
    d.addErrback(errsharesResponse,('mtred'))
    d.addErrback(log.err)

def mineco_getshares():
    d = getPage('https://mineco.in/stats.json')
    d.addCallback(mineco_sharesResponse)
    d.addErrback(errsharesResponse,('mineco'))
    d.addErrback(log.err)

def bitclockers_getshares():
    d = getPage('https://bitclockers.com/api')
    d.addCallback(bitclockers_sharesResponse)
    d.addErrback(errsharesResponse,('bitclockers'))
    d.addErrback(log.err)

def update_servers():
    global servers
    bclc_getshares()
    mtred_getshares()
    bitclockers_getshares()
    mineco_getshares()

@defer.inlineCallbacks
def delag_server():
    log.msg( 'Trying to delag')
    global servers
    global json_agent
    for index in servers:
        server = servers[index]
        if server['lag'] == True:
            data = yield work.jsonrpc_call(json_agent, server)
            if data != None:
                server['lag'] = False
    

def bitHopper_Post(request):
   
    request.setHeader('X-Long-Polling', 'http://localhost:8337')
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

    log.msg('RPC request ' + str(data) + " From " + str(pool_server['name']))
    work.jsonrpc_getwork(json_agent, pool_server, data, j_id, request, get_new_server, set_lp)

    return server.NOT_DONE_YET

def bitHopperLP(value, *methodArgs):
    log.msg('LP Client Side Reset')
    request = methodArgs[0]
    #Duplicated from above because its a little less of a hack
    #But apparently people expect well formed json-rpc back but won't actually make the call 
    json_request = request.content.read()
    try:
        rpc_request = json.loads(json_request)
    except exceptions.ValueError, e:
        rpc_request = {'params':[],'id':1}
    #Check for data to be validated
    global servers
    global current_server
    global json_agent
    pool_server=servers[current_server]
    
    data = rpc_request['params']
    j_id = rpc_request['id']

    log.msg('LP RPC request ' + str(data) + " From " + str(pool_server['name']))
    work.jsonrpc_getwork(json_agent, pool_server, data, j_id, request, get_new_server, set_lp)

    return None

class bitSite(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        new_server.addCallback(bitHopperLP, (request))
        return server.NOT_DONE_YET

    def render_POST(self, request):
        return bitHopper_Post(request)


    def getChild(self,name,request):
        return self

def main():
    log.startLogging(sys.stdout)
    site = server.Site(bitSite())
    reactor.listenTCP(8337, site)
    reactor.suggestThreadPoolSize(10)
    update_call = LoopingCall(update_servers)
    update_call.start(57)
    delag_call = LoopingCall(delag_server)
    delag_call.start(132)
    reactor.run()

if __name__ == "__main__":
    main()

