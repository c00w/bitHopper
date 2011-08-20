#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.


import os
import json
import sys
from twisted.web import server, resource
from twisted.web.http import UNAUTHORIZED

class dynamicSite(resource.Resource):
    def __init__(self, bitHopper):
        resource.Resource.__init__(self)
        self.bh = bitHopper
      
    isleaF = True
    def render_GET(self, request):
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
        linestring = index_file.read()
        index_file.close()
        request.write(linestring)
        request.finish()
        return server.NOT_DONE_YET

    def render_POST(self, request):
        for v in request.args:
            if "role" in v:
                try:
                    server = v.split('-')[1]
                    self.bh.pool.get_entry(server)['role'] = request.args[v][0]
                    self.bh.pool.get_entry(server)['refresh_time'] = 60
                    if request.args[v][0] in ['mine','info']:
                        self.bh.pool.update_api_server(server)

                except Exception, e:
                    self.bh.log_msg('Incorrect http post request role')
                    self.bh.log_msg(e)
            if "payout" in v:
                try:
                    server = v.split('-')[1]
                    self.bh.update_payout(server, float(request.args[v][0]))
                except Exception, e:
                    self.bh.log_dbg('Incorrect http post request payout')
                    self.bh.log_dbg(e)
            if "penalty" in v:
                try:
                    server = v.split('-')[1]
                    info = self.bh.pool.get_entry(server)
                    info['penalty'] = float(request.args[v][0])                    
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
          
        return self.render_GET(request)

class flatSite(resource.Resource):

    def __init__(self, bitHopper):
        resource.Resource.__init__(self)
        self.bitHopper = bitHopper

    isLeaf = True
    def render_GET(self, request):
        flat_info(request, self.bitHopper)
        return server.NOT_DONE_YET

    #def render_POST(self, request):
    #     global new_server
    #     bithopper_global.new_server.addCallback(bitHopperLP, (request))
    #     return server.NOT_DONE_YET


    def getChild(self, name, request):
        return self

class dataSite(resource.Resource):

    def __init__(self, bitHopper):
        resource.Resource.__init__(self)
        self.bitHopper = bitHopper

    isLeaf = True
    def render_GET(self, request):

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
        request.write(response)
        request.finish()
        return server.NOT_DONE_YET

    #def render_POST(self, request):
    #     bithopper_global.new_server.addCallback(bitHopperLP, (request))
    #     return server.NOT_DONE_YET

class lpSite():

    def __init__(self, bitHopper):
        self.bitHopper = bitHopper

    def handle(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/json')])
        return self.bitHopper.bitHopperLP()

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
            if env['PATH_INFO'] == 'flat':
                site = flatSite(self.bitHopper)
            elif env['PATH_INFO'] in ['stats', 'index.html']:
                site = dynamicSite(self.bitHopper)
            elif env['PATH_INFO'] == 'data':
                site = dataSite(self.bitHopper)
            else:
                site = self
        return site.handle(env,start_response)

    def handle(self, env, start_response):
        return self.bitHopper.work.handle(env, start_response)

    def auth(self, env):
        return True
        if self.bitHopper.auth != None:  
            user = None
            password = None
            if user != self.bitHopper.auth[0] or password != self.bitHopper.auth[1]:
                return False
        return True
