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

import sys
import exceptions
import optparse
import time
import lp
import os.path

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
        self.difficultyThreshold = 0.43
        
        self.pool.setup(self)

    def reject_callback(self,server,data):
        try:
            if data != []:
                self.db.update_rejects(server,1)
                self.pool.get_servers()[server]['rejects'] += 1
        except Exception, e:
            self.log_dbg('reject_callback_error')
            self.log_dbg(str(e))
            return

    def data_callback(self,server,data, user, password):
        try:
            if data != []:
                self.speed.add_shares(1)
                self.db.update_shares(server, 1, user, password)
                self.pool.get_servers()[server]['user_shares'] +=1
        except Exception, e:
            self.log_dbg('data_callback_error')
            self.log_dbg(str(e))

    def update_payout(self,server,payout):
        self.db.set_payout(server,float(payout))
        self.pool.servers[server]['payout'] = float(payout)

    def lp_callback(self, ):
        reactor.callLater(0.1,self.new_server.callback,None)
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
        """selects the best server for pool hopping. If there is not good server it returns eligious"""
        server_name = None
        difficulty = self.difficulty.get_difficulty()
        nmc_difficulty = self.difficulty.get_nmc_difficulty()
        min_shares = difficulty * self.difficultyThreshold
        
        for server in self.pool.get_servers():
            info = self.pool.get_entry(server)
            info['shares'] = int(info['shares'])
            if info['role'] not in ['mine','mine_nmc','mine_slush']:
                continue
            if info['role'] == 'mine':
                    shares = info['shares']
            elif info['role'] == 'mine_slush':
                shares = info['shares'] * 4
            elif info['role'] == 'mine_nmc':
                shares = info['shares']*difficulty / nmc_difficulty
            else:
                shares = 100* info['shares'] 
            if shares< min_shares and info['lag'] == False:
                min_shares = shares
                server_name = server

        if server_name == None:
            reject_rate = 1
            for server in self.pool.get_servers():
                info = self.pool.get_entry(server)
                if info['role'] != 'backup':
                    continue
                if info['lag'] == False:
                    rr_server = float(info['rejects'])/(info['user_shares']+1)
                    if  rr_server < reject_rate:
                        server_name = server
                        reject_rate = rr_server

        if server_name == None:
            min_shares = 10**10
            for server in self.pool.get_servers():
                info = self.pool.get_entry(server)
                if info['role'] not in ['mine','mine_nmc','mine_slush']:
                    continue
                if info['role'] == 'mine':
                    shares = info['shares']
                elif info['role'] == 'mine_slush':
                    shares = info['shares'] * 4
                elif info['role'] == 'mine_nmc':
                    shares = info['shares']*difficulty / nmc_difficulty
                else:
                    shares = info['shares'] 
                if shares< min_shares and info['lag'] == False:
                    min_shares = shares
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
        valid_roles = ['mine', 'mine_slush','mine_nmc']
        if self.pool.get_entry(self.pool.get_current())['role'] not in valid_roles:
            self.select_best_server()
            return

        current_role = self.pool.get_entry(self.pool.get_current())['role']
        if current_role == 'mine':
            difficulty = self.difficulty.get_difficulty()
        if current_role == 'mine_nmc':
            difficulty = self.difficulty.get_nmc_difficulty()
        if current_role == 'mine_slush':
            difficulty = self.difficulty.get_difficulty() * 4
        if self.pool.get_entry(self.pool.get_current())['shares'] > (difficulty * self.difficultyThreshold):
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
        bithopper_global.data_callback(current,data, request.getUser(), request.getPassword())
    if bithopper_global.options.debug:
        bithopper_global.log_msg('RPC request ' + str(data) + " submitted to " + str(pool_server['name']))
    else:
        if data == []:
            """ If request contains no data, tell the user which remote procedure was called instead """
            rep = rpc_request['method']
        else:
            rep = str(data[0][155:163])
        bithopper_global.log_msg('RPC request [' + rep + "] submitted to " + str(pool_server['name']))
    work.jsonrpc_getwork(bithopper_global.json_agent, pool_server, data, j_id, request, bithopper_global.get_new_server, bithopper_global.lp.set_lp, bithopper_global)

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

        work.jsonrpc_getwork(bithopper_global.json_agent, pool_server, data, j_id, request, bithopper_global.get_new_server, bithopper_global.lp.set_lp, bithopper_global)

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
    current_name = bithopper_global.pool.get_entry(bithopper_global.pool.get_current())['name']
    response += '<p>Current Pool: ' + current_name+' @ ' + str(bithopper_global.speed.get_rate()) + 'MH/s</p>'
    response += '<table border="1"><tr><td>Name</td><td>Role</td><td>Shares'
    response += '</td><td>Rejects</td><td>Payouts</td><td>Efficiency</td></tr>'
    servers = bithopper_global.pool.get_servers()
    for server in servers:
        info = servers[server]
        if info['role'] not in ['backup','mine', 'api_disable']:
            continue
        shares = str(bithopper_global.db.get_shares(server))
        rejects = bithopper_global.pool.get_servers()[server]['rejects']
        rejects_str = "{:.3}%".format(float(rejects/(float(shares)+1)*100)) + "(" + str(rejects)+")"
        response += '<tr><td>' + info['name'] + '</td><td>' + info['role'] + \
                      '</td><td>' + shares + \
                      '</td><td>' + rejects_str +\
                      '</td><td>' + str(bithopper_global.db.get_payout(server)) + \
                      '</td><td>' + str(bithopper_global.stats.get_efficiency(server)) \
                      + '</td></tr>'

    response += '</table></body></html>'
    request.write(response)
    request.finish()
    return

class flatSite(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        flat_info(request)
        return server.NOT_DONE_YET

    #def render_POST(self, request):
    #    global new_server
    #    bithopper_global.new_server.addCallback(bitHopperLP, (request))
    #    return server.NOT_DONE_YET


    def getChild(self,name,request):
        return self

class dataSite(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        response = json.dumps({"current":bithopper_global.pool.get_current(), 'mhash':bithopper_global.speed.get_rate(), 'difficulty':bithopper_global.difficulty.get_difficulty(), 'servers':bithopper_global.pool.get_servers()})
        request.write(response)
        request.finish()
        return server.NOT_DONE_YET

    #def render_POST(self, request):
    #    global new_server
    #    bithopper_global.new_server.addCallback(bitHopperLP, (request))
    #    return server.NOT_DONE_YET

class dynamicSite(resource.Resource):
    isleaF = True
    def render_GET(self,request):
        try:
            index = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
        except:
            index = 'index.html'
        file = open(index, 'r')
        linestring = file.read()
        file.close
        request.write(linestring)
        request.finish()
        return server.NOT_DONE_YET

    def render_POST(self, request):
        for v in request.args:
            if "role" in v:
                try:
                    server = v.split('-')[1]
                    bithopper_global.pool.get_entry(server)['role'] = request.args[v][0]
                    if request.args[v][0] in ['mine','info']:
                        bithopper_global.pool.update_api_server(server)

                except Exception,e:
                    bithopper_global.log_msg('Incorrect http post request role')
                    bithopper_global.log_msg(e)
            if "payout" in v:
                try:
                    server = v.split('-')[1]
                    bithopper_global.update_payout(server, float(request.args[v][0]))
                except Exception,e:
                    bithopper_global.log_dbg('Incorrect http post request payout')
                    bithopper_global.log_dbg(e)
        return self.render_GET(request)

class lpSite(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        bithopper_global.new_server.addCallback(bitHopperLP, (request))
        return server.NOT_DONE_YET

    def render_POST(self, request):
        bithopper_global.new_server.addCallback(bitHopperLP, (request))
        return server.NOT_DONE_YET

class bitSite(resource.Resource):

    def render_GET(self, request):
        bithopper_global.new_server.addCallback(bitHopperLP, (request))
        return server.NOT_DONE_YET

    def render_POST(self, request):
        return bitHopper_Post(request)


    def getChild(self,name,request):
        #bithopper_global.log_msg(str(name))
        if name == 'LP':
            return lpSite()
        elif name == 'flat':
            return flatSite()
        elif name == 'stats':
            return dynamicSite()
        elif name == 'data':
            return dataSite()
        return self

def parse_server_disable(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(','))
    
def select_scheduler(option, opt, value, parser):
    fudge = "fun"

def main():
    parser = optparse.OptionParser(description='bitHopper')
    parser.add_option('--noLP', action = 'store_true' ,default=False, help='turns off client side longpolling')
    parser.add_option('--debug', action= 'store_true', default = False, help='Use twisted output')
    parser.add_option('--listschedulers', action='store_true', default = False, help='List alternate schedulers available')
    parser.add_option('--list', action= 'store_true', default = False, help='List servers')
    parser.add_option('--disable', type=str, default = None, action='callback', callback=parse_server_disable, help='Servers to disable. Get name from --list. Servera,Serverb,Serverc')
    parser.add_option('--port', type = int, default=8337, help='Port to listen on')
    parser.add_option('--scheduler', type=str, default=None, help='Select an alternate scheduler')
    parser.add_option('--threshold', type=float, default=0.43, help='Override difficulty threshold (default 0.43)')
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
        print "Selecting scheduler: " + options.scheduler
        foundScheduler = False
        for s in Scheduler.__subclasses__():
            if s.__name__ == options.scheduler:
                bithopper_global.scheduler = s(bithopper_global)
                foundScheduler = True
                break
        if foundScheduler == False:
            print "Error couldn't find: " + options.scheduler + ". Using default scheduler."
    
    if options.threshold:
        bithopper_global.log_msg("Override difficulty threshold to: " + str(options.threshold))
        bithopper_global.difficultyThreshold = options.threshold

    if options.disable != None:
        for k in options.disable:
            if k in bithopper_global.pool.get_servers():
                if bithopper_global.pool.get_servers()[k]['role'] == 'backup':
                    print "You just disabled the backup pool. I hope you know what you are doing"
                bithopper_global.pool.get_servers()[k]['role'] = 'disable'
            else:
                print k + " Not a valid server"

    if options.debug: log.startLogging(sys.stdout)
    site = server.Site(bitSite())
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
