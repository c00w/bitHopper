#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.


from eventlet.green import os
import json
import sys

import webob

class dynamicSite():
    def __init__(self, bitHopper):
        self.bh = bitHopper

    def handle(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/html')])
        #Handle Possible Post values
        self.handle_POST(webob.Request(env))

        index_name = 'index.html'
        try:
            # determine scheduler index.html
            if hasattr(self.bh.scheduler,'index_html'):
                index_name = self.bh.scheduler.index_html
            # determine if application is a script file or frozen exe
            if hasattr(sys, 'frozen'):
                application_path = os.path.dirname(sys.executable)
            elif __file__:
                application_path = os.path.dirname(__file__)          
            index = os.path.join(application_path, index_name)
        except:
            index = os.path.join(os.curdir, index_name)
        index_file = open(index, 'r')
        line_string = index_file.read()
        index_file.close()
        return line_string

    def handle_POST(self, request):
        for v in request.POST:
            if "role" in v:
                try:
                    server = v.split('-')[1]
                    self.bh.pool.get_entry(server)['role'] = request.POST[v][0]
                    self.bh.pool.get_entry(server)['refresh_time'] = 60
                    if request.args[v][0] in ['mine','info']:
                        self.bh.pool.update_api_server(server)

                except Exception, e:
                    self.bh.log_msg('Incorrect http post request role')
                    self.bh.log_msg(e)
            if "payout" in v:
                try:
                    server = v.split('-')[1]
                    self.bh.update_payout(server, float(request.POST[v][0]))
                except Exception, e:
                    self.bh.log_dbg('Incorrect http post request payout')
                    self.bh.log_dbg(e)
            if "penalty" in v:
                try:
                    server = v.split('-')[1]
                    info = self.bh.pool.get_entry(server)
                    info['penalty'] = float(request.POST[v][0])                    
                    self.bh.select_best_server()
                except Exception, e:
                    self.bh.log_dbg('Incorrect http post request payout')
                    self.bh.log_dbg(e)
            if "resetscheduler" in v:
                self.bh.log_msg('User forced scheduler reset')
                try:
                    if hasattr(self.bh.scheduler, 'reset'):
                        self.bh.scheduler.reset()
                        self.bh.select_best_server()
                except Exception,e:
                    self.bh.log_dbg('Incorrect http post resetscheduler')
                    self.bh.log_dbg(e)
            if "resetshares" in v:
                self.bh.log_msg('User forced resetshares')
                try:
                    for server in self.bh.pool.get_servers():
                        info = self.bh.pool.get_entry(server)
                        info['shares'] = self.bh.difficulty.get_difficulty()
                except Exception,e:
                    self.bh.log_dbg('Incorrect http post resetshares')
                    self.bh.log_dbg(e)
            if "reloadconfig" in v:
                self.bh.log_msg('User forced configuration reload')
                try:
                    self.bh.pool.loadConfig(self.bh)
                except Exception,e:
                    self.bh.log_dbg('Incorrect http post reloadconfig')
                    self.bh.log_dbg(e)
            if "resetUserShares" in v:
                self.bh.log_msg('User forced user shares, est payouts to be reset')
                try:
                    for server in self.bh.pool.get_servers():
                        info = self.bh.pool.get_entry(server)
                        info['user_shares'] = 0
                        info['rejects'] = 0
                        info['expected_payout'] = 0
                except Exception,e:
                    self.bh.log_dbg('Incorrect http post resetUserShares')
                    self.bh.log_dbg(e)

class dataSite():

    def __init__(self, bitHopper):
        self.bitHopper = bitHopper

    def handle(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/json')])
        #Slice Info
        if hasattr(self.bitHopper.scheduler, 'sliceinfo'):
            sliceinfo = self.bitHopper.scheduler.sliceinfo
        else:
            sliceinfo = None

        lp = self.bitHopper.lp.lastBlock
        if lp == None:
            lp = {}
        else :
            lp = self.bitHopper.lp.blocks[lp]
        response = json.dumps({
            "current":self.bitHopper.pool.get_current(), 
            'mhash':self.bitHopper.speed.get_rate(), 
            'difficulty':self.bitHopper.difficulty.get_difficulty(),
            'sliceinfo':sliceinfo,
            'servers':self.bitHopper.pool.get_servers(),
            'user':self.bitHopper.data.get_users()})
        return response

    #def render_POST(self, request):
    #     bithopper_global.new_server.addCallback(bitHopperLP, (request))
    #     return server.NOT_DONE_YET

class lpSite():

    def __init__(self, bitHopper):
        self.bitHopper = bitHopper

    def handle(self, env, start_response):
        return self.bitHopper.work.handle_LP(env, start_response)

class nullsite():
    def __init__(self):
        pass

    def handle(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return ['']

class bitSite():

    def __init__(self, bitHopper):
        self.bitHopper = bitHopper

    def handle_start(self, env, start_response):
        if env['PATH_INFO'] in ['','/']:
            site = self
        elif env['PATH_INFO'] == '/LP':
            site = lpSite(self.bitHopper)
        elif not self.auth(env):
            site = nullsite()
        else:
            if env['PATH_INFO'] in ['/stats', '/index.html', '/index.htm']:
                site = dynamicSite(self.bitHopper)
            elif env['PATH_INFO'] == '/data':
                site = dataSite(self.bitHopper)
            else:
                site = self
        return site.handle(env,start_response)

    def handle(self, env, start_response):
        return self.bitHopper.work.handle(env, start_response)

    def auth(self, env):
        return True
        if self.bitHopper.auth != None:  
            data = env.get('HTTP_AUTHORIZATION').split(None, 1)[1]
            username, password = data.decode('base64').split(':', 1)
            if user != self.bitHopper.auth[0] or password != self.bitHopper.auth[1]:
                return False
        return True
