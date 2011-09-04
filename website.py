#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.


from eventlet.green import os, socket
import json
import sys

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

import traceback
import webob

class dynamicSite():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        index_name = 'index.html'
        self.site_names = ['/stats', '/index.html', '/index.htm']
        try:
            # determine scheduler index.html
            if hasattr(self.bitHopper.scheduler,'index_html'):
                index_name = self.bitHopper.scheduler.index_html
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
                    self.bitHopper.pool.get_entry(server)['role'] = request.POST[v]
                    self.bitHopper.pool.get_entry(server)['refresh_time'] = 60
                    if request.POST[v] in ['mine','info']:
                        self.bitHopper.pool.update_api_server(server)

                except Exception, e:
                    self.bitHopper.log_msg('Incorrect http post request role')
                    self.bitHopper.log_msg(e)
            if "payout" in v:
                try:
                    server = v.split('-')[1]
                    self.bitHopper.update_payout(server, float(request.POST[v]))
                except Exception, e:
                    self.bitHopper.log_msg('Incorrect http post request payout: ' + str(e))
            if "expout" in v:
                try:
                    server = v.split('-')[1]
                    for loopServer in self.bitHopper.pool.get_servers():
                        if loopServer == server:
                            info = self.bitHopper.pool.get_entry(loopServer)
                            info['expected_payout'] = float(request.POST[v])
                            userShares = info['expected_payout'] * self.bitHopper.difficulty.get_difficulty() / 50
                            info['user_shares'] = int(userShares)
                            self.bitHopper.db.get_shares(server)
                            self.bitHopper.log_msg('Expected payout for ' + str(server) + " modified")
                except Exception, e:
                    self.bitHopper.log_msg('Incorrect http post request for expected payout: ' + str(e))
            if "penalty" in v:
                try:
                    server = v.split('-')[1]
                    info = self.bitHopper.pool.get_entry(server)
                    old_penalty = 1
                    if 'penalty' in info:
                        old_penalty = info['penalty']
                    new_penalty = float(request.POST[v])
                    self.bitHopper.log_msg('Set ' + server + ' penalty from ' + str(old_penalty) + ' to ' + str(new_penalty))
                    info['penalty'] = new_penalty                    
                    self.bitHopper.select_best_server()
                except Exception, e:
                    self.bitHopper.log_msg('Incorrect http post request penalty: ' + str(v))
                    self.bitHopper.log_msg(e)
            if "resetscheduler" in v:
                self.bitHopper.log_msg('User forced scheduler reset')
                try:
                    if hasattr(self.bitHopper.scheduler, 'reset'):
                        self.bitHopper.scheduler.reset()
                        self.bitHopper.select_best_server()
                except Exception,e:
                    self.bitHopper.log_msg('Incorrect http post resetscheduler: ' + str(e))
            if "resetshares" in v:
                self.bitHopper.log_msg('User forced resetshares')
                try:
                    for server in self.bitHopper.pool.get_servers():
                        info = self.bitHopper.pool.get_entry(server)
                        info['shares'] = self.bitHopper.difficulty.get_difficulty()
                except Exception,e:
                    self.bitHopper.log_msg('Incorrect http post resetshares: ' + str(e))
            if "reloadconfig" in v:
                self.bitHopper.log_msg('User forced configuration reload')
                try:
                    self.bitHopper.reloadConfig()
                except Exception,e:
                    self.bitHopper.log_msg('Incorrect http post reloadconfig: ' + str(e))
                    if self.bitHopper.options.debug:
                        traceback.print_exc()
            if "resetUserShares" in v:
                self.bitHopper.log_msg('User forced user shares, est payouts to be reset')
                try:
                    for server in self.bitHopper.pool.get_servers():
                        info = self.bitHopper.pool.get_entry(server)
                        info['user_shares'] = 0
                        info['rejects'] = 0
                        info['expected_payout'] = 0
                except Exception,e:
                    self.bitHopper.log_msg('Incorrect http post resetUserShares: ' + str(e))
            if "resetUShares" in v:
                self.bitHopper.log_msg('User forced user shares to be reset')
                try:
                    for server in self.bitHopper.pool.get_servers():
                        info = self.bitHopper.pool.get_entry(server)
                        info['user_shares'] = 0
                        info['rejects'] = 0
                except Exception,e:
                    self.bitHopper.log_msg('Incorrect http post resetUserShares: ' + str(e))
            if "resetEstPayout" in v:
                self.bitHopper.log_msg('User forced est payouts to be reset')
                try:
                    for server in self.bitHopper.pool.get_servers():
                        info = self.bitHopper.pool.get_entry(server)
                        info['expected_payout'] = 0
                except Exception,e:
                    self.bitHopper.log_msg('Incorrect http post resetEstPayout: ' + str(e))
            if "enableDebug" in v:
                self.bitHopper.log_dbg('User enabled DEBUG from web')
                self.bitHopper.options.debug = True
            if "disableDebug" in v:
                self.bitHopper.options.debug = False
                self.bitHopper.log_msg('User disabled DEBUG from web')
            if "setLPPenalty" in v:
                try:
                    server = v.split('-')[1]
                    info = self.bitHopper.pool.get_entry(server)
                    old_lp_penalty = 0
                    if 'lp_penalty' in info:
                        old_lp_penalty = info['lp_penalty']
                    new_lp_penalty = float(request.POST[v])
                    self.bitHopper.log_msg("Updating LP Penalty for " + server + " from " + str(old_lp_penalty) + ' to ' + str(new_lp_penalty))
                    info['lp_penalty'] = new_lp_penalty
                except Exception, e:
                    self.bitHopper.log_msg('Incorrect http post request setLPPenalty: ' + str(v))
                    self.bitHopper.log_msg(e)


class dataSite():

    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.site_names = ['/data']

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
            'ixc_difficulty':self.bitHopper.difficulty.get_ixc_difficulty(),
            'i0c_difficulty':self.bitHopper.difficulty.get_i0c_difficulty(),
            'nmc_difficulty':self.bitHopper.difficulty.get_nmc_difficulty(),
            'scc_difficulty':self.bitHopper.difficulty.get_scc_difficulty(),
            'sliceinfo':sliceinfo,
            'servers':self.bitHopper.pool.get_servers(),
            'user':self.bitHopper.data.get_users()})
        return response

class lpSite():

    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.site_names = ['/LP']
        self.auth = False

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
        self.auth = False
        self.site_names = ['','/']
        self.bitHopper = bitHopper
        self.dynamicSite = dynamicSite(self.bitHopper)
        self.sites = [self, lpSite(self.bitHopper), dynamicSite(self.bitHopper), dataSite(self.bitHopper)]

    def handle_start(self, env, start_response):
        use_site = self
        for site in self.sites:
            if getattr(site, 'auth', True):
                if not self.auth_check(env):
                    use_site = nullsite()
                    break
            if env['PATH_INFO'] in site.site_names:
                use_site = site
                break
        try:
            return use_site.handle(env,start_response)
        except Exception, e:
            self.bitHopper.log_msg('Error in a wsgi function')
            self.bitHopper.log_msg(e)
            #traceback.print_exc()
            return [""]

    def handle(self, env, start_response):
        return self.bitHopper.work.handle(env, start_response)

    def auth_check(self, env):
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
