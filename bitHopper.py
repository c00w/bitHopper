#!/bin/env python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import work
import diff
import stats
import pool

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

class BitHopper():
    def __init__(self):
        self.json_agent = Agent(reactor)
        self.lp_agent = Agent(reactor, persistent=True)
        self.new_server = Deferred()
        self.stats_file = None
        self.options = None
        self.pool = pool.Pool()
        self.lp = lp.LongPoll(self)
        self.db = database.Database(self)
        self.stats = stats.Statistics(self)

    def data_callback(self,server,data):
        if data != []:
            self.db.update_shares(server, 1)

    def lp_callback(self, ):
        reactor.callLater(0.1,self.new_server.callback,None)
        self.new_server = Deferred()

    def get_json_agent(self, ):
        return self.json_agent

    def get_lp_agent(self, ):
        return self.lp_agent

    def get_options(self, ):
        return self.options

    def log_msg(self, msg):
        if self.get_options() == None:
            print time.strftime("[%H:%M:%S] ") +str(msg)
            return
        if self.get_options().debug == True:
            log.msg(msg)
            return
        print time.strftime("[%H:%M:%S] ") +str(msg)

    def log_dbg(self, msg):
        if self.get_options() == None:
            log.err(msg)
            return
        if self.get_options().debug == True:
            log.err(msg)
            return
        return

    def get_server(self, ):
        return self.pool.get_current()

    def select_best_server(self, ):
        """selects the best server for pool hopping. If there is not good server it returns eligious"""
        server_name = None
        difficulty = diff.difficulty

        min_shares = difficulty*.40
        
        for server in self.pool.get_servers():
            info = self.pool.get_entry(server)
            if info['role'] != 'mine':
                continue
            if info['shares']< min_shares and info['lag'] == False:
                min_shares = info['shares']
                server_name = server

        if server_name == None:
            for server in self.pool.get_servers():
                info = self.pool.get_entry(server)
                if info['role'] != 'backup':
                    continue
                if info['lag'] == False:
                    server_name = server
                    break

        if server_name == None:
            min_shares = 10**10
            for server in self.pool.get_servers():
                info = self.pool.get_entry(server)
                if info['role'] != 'mine':
                    continue
                if info['shares']< min_shares and info['lag'] == False:
                    min_shares = info['shares']
                    server_name = server

        if server_name == None:
            for server in self.pool.get_servers():
                info = self.pool.get_entry(server)
                if info['role'] != 'backup':
                    continue
                server_name = server
                break

        global new_server

        if self.pool.get_current() != server_name:
            self.pool.set_current(server_name)
            self.log_msg("Server change to " + str(self.pool.get_current()) + ", telling client with LP")
            self.lp_callback()      
            self.lp.clear_lp()
            
        return

    def get_new_server(self, server):
        if server != self.pool.get_entry(self.pool.get_current()):
            return self.pool.get_entry(self.pool.get_current())
        self.pool.get_entry(self.pool.get_current())['lag'] = True
        self.select_best_server()
        return self.pool.get_entry(self.pool.get_current())

    def server_update(self, ):

        if self.pool.get_entry(self.pool.get_current())['shares'] > diff.difficulty * .40:
            self.select_best_server()
            return

        min_shares = 10**10

        for server in self.pool.get_servers():
            if self.pool.get_entry(server)['shares'] < min_shares:
                min_shares = self.pool.get_entry(server)['shares']

        if min_shares < self.pool.get_entry(self.pool.get_current())['shares']*.90:
            self.select_best_server()
            return



    @defer.inlineCallbacks
    def delag_server(self ):
        self.log_dbg('Running Delager')
        for index in self.pool.get_servers():
            server = self.pool.get_entry(index)
            if server['lag'] == True:
                data = yield work.jsonrpc_call(self.json_agent, server,[], None)
                if data != None:
                    server['lag'] = False

bithopper_global = BitHopper()

def bitHopper_Post(request):
    if not bithopper_global.options.noLP:
        request.setHeader('X-Long-Polling', '/LP')
    rpc_request = json.loads(request.content.read())
    #check if they are sending a valid message
    if rpc_request['method'] != "getwork":
        return json.dumps({'result':None, 'error':'Not supported', 'id':rpc_request['id']})


    #Check for data to be validated
    current = bithopper_global.pool.get_current()
    pool_server=bithopper_global.pool.get_entry(current)
    
    data = rpc_request['params']
    j_id = rpc_request['id']
    if data != []:
        self.data_callback(current,data)
    if bithopper_global.options.debug:
        bithopper_global.log_msg('RPC request ' + str(data) + " submitted to " + str(pool_server['name']))
    else:
        if data == []:
            rep = ""
        else:
            rep = str(data[0][155:163])
        bithopper_global.log_msg('RPC request [' + rep + "] submitted to " + str(pool_server['name']))
    work.jsonrpc_getwork(bithopper_global.json_agent, pool_server, data, j_id, request, bithopper_global.get_new_server, bithopper_global.lp.set_lp)

    return server.NOT_DONE_YET

def bitHopperLP(value, *methodArgs):
    try:
        bithopper_global.log_msg('LP triggered serving miner')
        request = methodArgs[0]
        #Duplicated from above because its a little less of a hack
        #But apparently people expect well formed json-rpc back but won't actually make the call 
        try:
            json_request = request.content.read()
        except Exception,e:
            bithopper_global.log_dbg( 'reading request content failed')
            json_request = None
        try:
            rpc_request = json.loads(json_request)
        except Exception, e:
            bithopper_global.log_dbg('Loading the request failed')
            rpc_request = {'params':[],'id':1}
        #Check for data to be validated
        pool_server=bithopper_global.pool.get_entry(bithopper_global.pool.get_current())
        
        data = rpc_request['params']
        j_id = rpc_request['id']

        work.jsonrpc_getwork(bithopper_global.json_agent, pool_server, data, j_id, request, bithopper_global.get_new_server, bithopper_global.lp.set_lp)

    except Exception, e:
        bithopper_global.log_msg('Error Caught in bitHopperLP')
        bithopper_global.log_dbg(str(e))
        try:
            request.finish()
        except Exception, e:
            bithopper_global.log_dbg( "Client already disconnected Urgh.")

    return None

def flat_info(request):
    response = '<html><head><title>bitHopper Info</title></head><body>'
    response += '<p>Pools:</p>'
    response += '<tr><td>Name</td><td>Role</td><td>Shares</td><td>Payouts</td>\
<td>Efficiency</td></tr>'
    servers = bithopper_global.pool.get_servers()
    for server in servers:
        info = servers[server]
        response += '<tr><td>' + info['name'] + '</td><td>' + info['role'] + \
                      '</td><td>' + str(bithopper_global.db.get_shares(server)) + \
                      '</td><td>' + str(bithopper_global.db.get_payout(server)) + \
                      '</td><td>' + str(bithopper_global.stats.get_efficiency(server)) \
                      + '</td></tr>'

    response += '</body></html>'
    request.write(response)
    request.finish()
    return

class infoSite(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        print 'Website request'
        flat_info(request)
        return server.NOT_DONE_YET

    #def render_POST(self, request):
    #    global new_server
    #    bithopper_global.new_server.addCallback(bitHopperLP, (request))
    #    return server.NOT_DONE_YET


    def getChild(self,name,request):
        return self

class lpSite(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        bithopper_global.new_server.addCallback(bitHopperLP, (request))
        return server.NOT_DONE_YET

    def render_POST(self, request):
        bithopper_global.new_server.addCallback(bitHopperLP, (request))
        return server.NOT_DONE_YET


    def getChild(self,name,request):
        return self

class bitSite(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        bithopper_global.new_server.addCallback(bitHopperLP, (request))
        return server.NOT_DONE_YET

    def render_POST(self, request):
        return bitHopper_Post(request)


    def getChild(self,name,request):
        print name
        if name == 'LP':
            return lpSite()
        elif name == 'stats':
            return infoSite()
        return self

def parse_server_disable(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(','))
    

def main():
    parser = optparse.OptionParser(description='bitHopper')
    parser.add_option('--noLP', action = 'store_true' ,default=False, help='turns off client side longpolling')
    parser.add_option('--debug', action= 'store_true', default = False, help='Use twisted output')
    parser.add_option('--list', action= 'store_true', default = False, help='List servers')
    parser.add_option('--disable', type=str, default = None, action='callback', callback=parse_server_disable, help='Servers to disable. Get name from --list. Servera,Serverb,Serverc')
    parser.add_option('--database', action= 'store_true', default = False, help='dump stats to filename')
    args, rest = parser.parse_args()
    options = args
    bithopper_global.options = args

    if options.list:
        for k in bithopper_global.pool.get_servers():
            print k
        return
    
    for k in bithopper_global.pool.get_servers():
        bithopper_global.pool.get_servers()[k]['user_shares'] = 0

    if options.disable != None:
        for k in options.disable:
            if k in bithopper_global.pool.get_servers():
                if bithopper_global.pool.get_servers()[k]['role'] == 'backup':
                    print "You just disabled the backup pool. I hope you know what you are doing"
                bithopper_global.pool.get_servers()[k]['role'] = 'disable'
            else:
                print k + " Not a valid server"

    if options.database:
        database.check_database()

    if options.debug: log.startLogging(sys.stdout)
    site = server.Site(bitSite())
    reactor.listenTCP(8337, site)
    update_call = LoopingCall(bithopper_global.pool.update_api_servers, bithopper_global)
    update_call.start(117)
    delag_call = LoopingCall(bithopper_global.delag_server)
    delag_call.start(119)
    stats_call = LoopingCall(bithopper_global.stats.update_api_stats)
    stats_call.start(117*4)
    reactor.run()

if __name__ == "__main__":
    main()
