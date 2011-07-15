#!/bin/env python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import work
import diff
import stats

import database
import sys
import exceptions
import optparse
import time
import lp

from twisted.web import server, resource
from client import Agent
from _newclient import Request
from twisted.internet import reactor, defer
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
from twisted.python import log, failure




json_agent = Agent(reactor)
lp_agent = Agent(reactor, persistent=True)
new_server = Deferred()
stats_file = None
options = None

def data_callback(server, data):
    global options
    if options.database:
        database.update_shares(server, 1)

def data_shares(server,shares):
    global options
    if options.database:
        database.update_shares(server,shares)

def data_get_shares(server):
    global options
    if options.database:
        return database.get_shares(server)
    return 0

def data_payout(server,payout):
    global options
    if options.database:
        database.update_payout(server,payout)

def data_get_payout(server):
    global options
    if options.database:
        return database.get_payout(server)
    return 0

def lp_callback():
    global new_server
    reactor.callLater(0.1,new_server.callback,None)
    new_server = Deferred()

def get_json_agent():
    global json_agent
    return json_agent

def get_lp_agent():
    global lp_agent
    return lp_agent

def get_options():
    global options
    return options

def log_msg(msg):
    if get_options() == None:
        print time.strftime("[%H:%M:%S] ") +str(msg)
        return
    if get_options().debug == True:
        log.msg(msg)
        return
    print time.strftime("[%H:%M:%S] ") +str(msg)

def log_dbg(msg):
    if get_options() == None:
        log.err(msg)
        return
    if get_options().debug == True:
        log.err(msg)
        return
    return

import pool

def get_server():
    return pool.get_current()

def select_best_server():
    """selects the best server for pool hopping. If there is not good server it returns eligious"""
    global access
    server_name = None
    difficulty = diff.difficulty

    min_shares = difficulty*.40
    
    for server in pool.get_servers():
        info = pool.get_entry(server)
        if info['role'] != 'mine':
            continue
        if info['shares']< min_shares and info['lag'] == False:
            min_shares = info['shares']
            server_name = server

    if server_name == None:
        for server in pool.get_servers():
            info = pool.get_entry(server)
            if info['role'] != 'backup':
                continue
            if info['lag'] == False:
                server_name = server
                break

    if server_name == None:
        min_shares = 10**10
        for server in pool.get_servers():
            info = pool.get_entry(server)
            if info['role'] != 'mine':
                continue
            if info['shares']< min_shares and info['lag'] == False:
                min_shares = info['shares']
                server_name = server

    if server_name == None:
        for server in pool.get_servers():
            info = pool.get_entry(server)
            if info['role'] != 'backup':
                continue
            server_name = server
            break

    global new_server

    if pool.get_current() != server_name:
        pool.set_current(server_name)
        log_msg("Server change to " + str(pool.get_current()) + ", telling client with LP")
        lp_callback()      
        lp.clear_lp()
        
    return

def get_new_server(server):
    if server != pool.get_entry(pool.get_current()):
        return pool.get_entry(pool.get_current())
    pool.get_entry(pool.get_current())['lag'] = True
    select_best_server()
    return pool.get_entry(pool.get_current())

def server_update():

    if pool.get_entry(pool.get_current())['shares'] > diff.difficulty * .40:
        select_best_server()
        return

    min_shares = 10**10

    for server in pool.get_servers():
        if pool.get_entry(server)['shares'] < min_shares:
            min_shares = pool.get_entry(server)['shares']

    if min_shares < pool.get_entry(pool.get_current())['shares']*.90:
        select_best_server()
        return



@defer.inlineCallbacks
def delag_server():
    log_dbg('Running Delager')
    global json_agent
    for index in pool.get_servers():
        server = pool.get_entry(index)
        if server['lag'] == True:
            data = yield work.jsonrpc_call(json_agent, server,[], None)
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
    global json_agent
    current = pool.get_current()
    pool_server=pool.get_entry(current)
    
    data = rpc_request['params']
    j_id = rpc_request['id']
    if data != []:
        data_callback(current,data)

    log_msg('RPC request ' + str(data) + " submitted to " + str(pool_server['name']))
    work.jsonrpc_getwork(json_agent, pool_server, data, j_id, request, get_new_server, lp.set_lp)

    

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
        global json_agent
        pool_server=pool.get_entry(pool.get_current())
        
        data = rpc_request['params']
        j_id = rpc_request['id']

        work.jsonrpc_getwork(json_agent, pool_server, data, j_id, request, get_new_server, lp.set_lp)

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

def parse_server_disable(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(','))
    

def main():
    global options
    parser = optparse.OptionParser(description='bitHopper')
    parser.add_option('--noLP', action = 'store_true' ,default=False, help='turns off client side longpolling')
    parser.add_option('--debug', action= 'store_true', default = False, help='Use twisted output')
    parser.add_option('--list', action= 'store_true', default = False, help='List servers')
    parser.add_option('--disable', type=str, default = None, action='callback', callback=parse_server_disable, help='Servers to disable. Get name from --list. Servera,Serverb,Serverc')
    parser.add_option('--database', action= 'store_true', default = False, help='dump stats to filename')
    args, rest = parser.parse_args()
    options = args
    if options.list:
        for k in pool.get_servers():
            print k
        return
    
    for k in pool.get_servers():
        pool.get_servers()[k]['user_shares'] = 0

    if options.disable != None:
        for k in options.disable:
            if k in pool.get_servers():
                if pool.get_servers()[k]['role'] == 'backup':
                    print "You just disabled the backup pool. I hope you know what you are doing"
                pool.get_servers()[k]['role'] = 'disable'
            else:
                print k + " Not a valid server"

    if options.database:
        database.check_database()

    if options.debug: log.startLogging(sys.stdout)
    site = server.Site(bitSite())
    reactor.listenTCP(8337, site)
    update_call = LoopingCall(pool.update_api_servers)
    update_call.start(117)
    delag_call = LoopingCall(delag_server)
    delag_call.start(119)
    stats_call = LoopingCall(stats.update_api_stats)
    stats_call.start(117*4)
    reactor.run()

if __name__ == "__main__":
    main()
