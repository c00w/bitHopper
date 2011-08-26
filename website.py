#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.


from eventlet.green import os
import json
import sys
import traceback
import webob

class dynamicSite():
    def __init__(self, bitHopper):
        self.bh = bitHopper
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
        self.line_string = index_file.read()
        index_file.close()

    def handle(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/html')])

        #Handle Possible Post values
        self.handle_POST(webob.Request(env))

        return self.line_string

    def handle_POST(self, request):
        for v in request.POST:
            if "role" in v:
                try:
                    server = v.split('-')[1]
                    self.bh.pool.get_entry(server)['role'] = request.POST[v]
                    self.bh.pool.get_entry(server)['refresh_time'] = 60
                    if request.POST[v] in ['mine','info']:
                        self.bh.pool.update_api_server(server)

                except Exception, e:
                    self.bh.log_msg('Incorrect http post request role')
                    self.bh.log_msg(e)
            if "payout" in v:
                try:
                    server = v.split('-')[1]
                    self.bh.update_payout(server, float(request.POST[v]))
                except Exception, e:
                    self.bh.log_dbg('Incorrect http post request payout')
                    self.bh.log_dbg(e)
            if "penalty" in v:
                try:
                    server = v.split('-')[1]
                    info = self.bh.pool.get_entry(server)
                    old_penalty = 1
                    if 'penalty' in info:
                        old_penalty = info['penalty']
                    new_penalty = float(request.POST[v])
                    self.bh.log_msg('Set ' + server + ' penalty from ' + str(old_penalty) + ' to ' + str(new_penalty))
                    info['penalty'] = new_penalty                    
                    self.bh.select_best_server()
                except Exception, e:
                    self.bh.log_dbg('Incorrect http post request penalty: ' + str(v))
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
                    self.bh.reloadConfig()
                except Exception,e:
                    self.bh.log_dbg('Incorrect http post reloadconfig')
                    self.bh.log_dbg(e)
                    if self.bh.options.debug:
                        traceback.print_exc()
                        
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
            if "enableDebug" in v:
                self.bh.log_dbg('User enabled DEBUG from web')
                self.bh.options.debug = True
            if "disableDebug" in v:
                self.bh.options.debug = False
                self.bh.log_msg('User disabled DEBUG from web')
            if "setLPPenalty" in v:
                try:
                    server = v.split('-')[1]
                    info = self.bh.pool.get_entry(server)
                    old_lp_penalty = 0
                    if 'lp_penalty' in info:
                        old_lp_penalty = info['lp_penalty']
                    new_lp_penalty = float(request.POST[v])
                    self.bh.log_msg("Updating LP Penalty for " + server + " from " + str(old_lp_penalty) + ' to ' + str(new_lp_penalty))
                    info['lp_penalty'] = new_lp_penalty
                except Exception, e:
                    self.bh.log_dbg('Incorrect http post request setLPPenalty: ' + str(v))
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

class lpSite():

    def __init__(self, bitHopper):
        self.bitHopper = bitHopper

    def handle(self, env, start_response):
        return self.bitHopper.work.handle_LP(env, start_response)

class nullsite():
    def __init__(self):
        pass

    def handle(self, env, start_response):
        start_response('401 UNAUTHORIZED', [('Content-Type', 'text/plain'),('WWW-Authenticate','Basic realm="Protected"')])
        return ['']

class bitSite():

    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.dynamicSite = dynamicSite(self.bitHopper)

    def handle_start(self, env, start_response):
        if env['PATH_INFO'] in ['','/']:
            site = self
        elif env['PATH_INFO'] == '/LP':
            site = lpSite(self.bitHopper)
        elif not self.auth(env):
            site = nullsite()
        else:
            if env['PATH_INFO'] in ['/stats', '/index.html', '/index.htm']:
                site = self.dynamicSite
            elif env['PATH_INFO'] == '/data':
                site = dataSite(self.bitHopper)
            else:
                site = self
        try:
            return site.handle(env,start_response)
        except Exception, e:
            self.bitHopper.log_msg('Error in a wsgi function')
            self.bitHopper.log_msg(e)
            #traceback.print_exc()
            return [""]

    def handle(self, env, start_response):
        return self.bitHopper.work.handle(env, start_response)

    def auth(self, env):
        if self.bitHopper.auth != None:  
            if env.get('HTTP_AUTHORIZATION') == None:
                return False
            try:
                data = env.get('HTTP_AUTHORIZATION').split(None, 1)[1]
                username, password = data.decode('base64').split(':', 1)
                if username != self.bitHopper.auth[0] or password != self.bitHopper.auth[1]:
                    return False
            except Exception, e:
                self.bitHopper.log_msg(e)
                return False
        return True
