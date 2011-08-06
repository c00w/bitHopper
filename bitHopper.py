#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import work
import diff
import stats
import pool
import speed
import database
import scheduler
import website
import getwork_store
import data

import sys
import exceptions
import optparse
import time
import lp
import os.path
import os

from twisted.web import server, resource
from client import Agent
from _newclient import Request
from twisted.internet import reactor, defer
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
from twisted.python import log, failure
from scheduler import Scheduler

class BitHopper():
    def __init__(self):
        self.json_agent = Agent(reactor)
        self.lp_agent = Agent(reactor, persistent=True)
        self.new_server = Deferred()
        self.stats_file = None
        self.options = None
        self.reactor = reactor
        self.difficulty = diff.Difficulty(self)
        self.pool = pool.Pool(self)
        self.db = database.Database(self)
        self.lp = lp.LongPoll(self)
        self.speed = speed.Speed(self)
        self.stats = stats.Statistics(self)
        self.scheduler = scheduler.Scheduler(self)
        self.getwork_store = getwork_store.Getwork_store()
        self.data = data.Data(self)
        self.pool.setup(self)

    def reject_callback(self,server,data):
        self.data.reject_callback(server,data)

    def data_callback(self,server,data, user, password):
        self.data.data_callback(server, data, user, password)

    def update_payout(self,server,payout):
        self.db.set_payout(server,float(payout))
        self.pool.servers[server]['payout'] = float(payout)

    def lp_callback(self, work):
        if work == None:
            return
        reactor.callLater(0.1,self.new_server.callback,work)
        self.new_server = Deferred()

    def get_json_agent(self, ):
        return self.json_agent

    def get_lp_agent(self, ):
        return self.lp_agent

    def get_options(self, ):
        return self.options

    def log_msg(self, msg, **kwargs):
        if kwargs and kwargs.get('cat'):
            print time.strftime("[%H:%M:%S] ") + '[' + kwargs.get('cat') + '] ' + str(msg)
        elif self.get_options() == None:
            print time.strftime("[%H:%M:%S] ") +str(msg)
            sys.stdout.flush()
        elif self.get_options().debug == True:
            log.msg(msg)
            sys.stdout.flush()
        else: 
            print time.strftime("[%H:%M:%S] ") +str(msg)
            sys.stdout.flush()

    def log_dbg(self, msg, **kwargs):
        if self.get_options().debug == True and kwargs and kwargs.get('cat'):
            log.err('['+kwargs.get('cat')+"] "+msg)
            sys.stderr.flush()
        elif self.get_options() == None:
            log.err(msg)
            sys.stderr.flush()
        elif self.get_options().debug == True:
            log.err(msg)
            sys.stderr.flush()
        return

    def get_server(self, ):
        return self.pool.get_current()

    def select_best_server(self, ):
        server_name = None
        server_name = self.scheduler.select_best_server()
        if server_name == None:
            self.log_msg('FATAL Error, scheduler did not return any pool!')
            os._exit(-1)
            
        if self.pool.get_current() != server_name:
            self.pool.set_current(server_name)
            self.log_msg("Server change to " + str(self.pool.get_current()))

        return

    def get_new_server(self, server):
        if server != self.pool.get_entry(self.pool.get_current()):
            return self.pool.get_entry(self.pool.get_current())
        self.pool.get_entry(self.pool.get_current())['lag'] = True
        self.select_best_server()
        return self.pool.get_entry(self.pool.get_current())

    def server_update(self, ):
        if self.scheduler.server_update():
            self.select_best_server()

    @defer.inlineCallbacks
    def delag_server(self ):
        self.log_dbg('Running Delager')
        for index in self.pool.get_servers():
            server = self.pool.get_entry(index)
            if server['lag'] == True:
                data = yield work.jsonrpc_call(self.json_agent, server,[], self)
                if data != None:
                    server['lag'] = False

    def bitHopper_Post(self,request):
        if not self.options.noLP:
            request.setHeader('X-Long-Polling', '/LP')
        rpc_request = json.loads(request.content.read())
        #check if they are sending a valid message
        if rpc_request['method'] != "getwork":
            return json.dumps({'result':None, 'error':'Not supported', 'id':rpc_request['id']})

        #Check for data to be validated
        current = self.pool.get_current()

        data = rpc_request['params']
        j_id = rpc_request['id']
        if data != []:
            new_server = self.getwork_store.get_server(data[0][72:136])
            if new_server != None:
                current = new_server
        pool_server=self.pool.get_entry(current)

        work.jsonrpc_getwork(self.json_agent, pool_server, data, j_id, request, self)

        if self.options.debug:
            self.log_msg('RPC request ' + str(data) + " submitted to " + str(pool_server['name']))
        else:
            if data == []:
                #If request contains no data, tell the user which remote procedure was called instead
                rep = rpc_request['method']
            else:
                rep = str(data[0][155:163])
            self.log_msg('RPC request [' + rep + "] submitted to " + str(pool_server['name']))

        if data != []:
            self.data_callback(current,data, request.getUser(), request.getPassword())        
        return server.NOT_DONE_YET

    def bitHopperLP(self,value, *methodArgs):
        try:
            self.log_msg('LP triggered serving miner')
            request = methodArgs[0]
            #Duplicated from above because its a little less of a hack
            #But apparently people expect well formed json-rpc back but won't actually make the call
            try:
                json_request = request.content.read()
            except Exception,e:
                self.log_dbg( 'reading request content failed')
                json_request = None
            try:
                rpc_request = json.loads(json_request)
            except Exception, e:
                self.log_dbg('Loading the request failed')
                rpc_request = {'params':[],'id':1}

            j_id = rpc_request['id']

            response = json.dumps({"result":value,'error':None,'id':j_id})
            request.write(response)
            request.finish()

        except Exception, e:
            self.log_msg('Error Caught in bitHopperLP')
            self.log_dbg(str(e))
            try:
                request.finish()
            except Exception, e:
                self.log_dbg( "Client already disconnected Urgh.")

        return None

def parse_server_disable(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(','))

def select_scheduler(option, opt, value, parser):
    pass

bithopper_global = BitHopper()

def main():
    parser = optparse.OptionParser(description='bitHopper')
    parser.add_option('--noLP', action = 'store_true' ,default=False, help='turns off client side longpolling')
    parser.add_option('--debug', action= 'store_true', default = False, help='Use twisted output')
    parser.add_option('--listschedulers', action='store_true', default = False, help='List alternate schedulers available')
    parser.add_option('--list', action= 'store_true', default = False, help='List servers')
    parser.add_option('--disable', type=str, default = None, action='callback', callback=parse_server_disable, help='Servers to disable. Get name from --list. Servera,Serverb,Serverc')
    parser.add_option('--port', type = int, default=8337, help='Port to listen on')
    parser.add_option('--scheduler', type=str, default=None, help='Select an alternate scheduler')
    parser.add_option('--threshold', type=float, default=None, help='Override difficulty threshold (default 0.43)')
    parser.add_option('--altslicesize', type=int, default=900, help='Override Default AltSliceScheduler Slice Size of 900')
    parser.add_option('--altminslicesize', type=int, default=60, help='Override Default Minimum Pool Slice Size of 60 (AltSliceScheduler only)')
    parser.add_option('--altslicejitter', type=int, default=0, help='Add some random variance to slice size (default disabled)(AltSliceScheduler only)')
    args, rest = parser.parse_args()
    options = args
    bithopper_global.options = args
    
    if options.list:
        for k in bithopper_global.pool.get_servers():
            print k
        return

    if options.listschedulers:
        schedulers = None
        for s in Scheduler.__subclasses__():
            if schedulers != None: schedulers = schedulers + ", " + s.__name__
            else: schedulers = s.__name__
        print "Available Schedulers: " + schedulers
        return
    
    if options.scheduler:
        bithopper_global.log_msg("Selecting scheduler: " + options.scheduler)
        foundScheduler = False
        for s in Scheduler.__subclasses__():
            if s.__name__ == options.scheduler:
                bithopper_global.scheduler = s(bithopper_global)
                foundScheduler = True
                break
        if foundScheduler == False:            
            bithopper_global.log_msg("Error couldn't find: " + options.scheduler + ". Using default scheduler.")
            bithopper_global.scheduler = scheduler.DefaultScheduler(bithopper_global)
    else:
        bithopper_global.log_msg("Using default scheduler.")
        bithopper_global.scheduler = scheduler.DefaultScheduler(bithopper_global)

    bithopper_global.select_best_server()

    if options.disable != None:
        for k in options.disable:
            if k in bithopper_global.pool.get_servers():
                if bithopper_global.pool.get_servers()[k]['role'] == 'backup':
                    bithopper_global.log_msg("You just disabled the backup pool. I hope you know what you are doing")
                bithopper_global.pool.get_servers()[k]['role'] = 'disable'
            else:
                bithopper_global.log_msg(k + " Not a valid server")

    if options.debug: log.startLogging(sys.stdout)
    site = server.Site(website.bitSite(bithopper_global))
    reactor.listenTCP(options.port, site)
    reactor.callLater(0, bithopper_global.pool.update_api_servers, bithopper_global)
    delag_call = LoopingCall(bithopper_global.delag_server)
    delag_call.start(119)
    stats_call = LoopingCall(bithopper_global.stats.update_api_stats)
    stats_call.start(117*4)
    reactor.run()
    bithopper_global.db.close()

if __name__ == "__main__":
    main()
