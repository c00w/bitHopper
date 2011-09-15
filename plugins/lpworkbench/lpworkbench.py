from eventlet.green import os, socket
import json
import sys
import webob

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class lpWorkbench():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper        
        self.site_names = ['/lpworkbench']
        index_name = 'lpworkbench.html'
        try:
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

        index_name = 'lpworkbench.html'
        try:
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
        return self.line_string
    
    def handle_POST(self, request):
        for v in request.POST:
            if "setOwner" in v:
                try:
                    blockhash = v.split('-')[1]
                    block = self.bitHopper.lp.blocks[blockhash]
                    old_owner = None
                    if block != None and '_owner' in block:
                        old_owner = self.bitHopper.lp.blocks[blockhash]['_owner']
                    new_owner = str(request.POST[v])
                    self.bitHopper.log_msg("Updating Block Owner " + blockhash + " from " + str(old_owner) + ' to ' + str(new_owner))
                    self.bitHopper.lp.set_owner(new_owner, blockhash)
                except Exception, e:
                    self.bitHopper.log_dbg('Incorrect http post request setOwner: ' + str(v))
                    traceback.print_exc()

class lpWorkbenchDataSite():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.site_names = ['/lpworkbenchdata']

    def handle(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/json')])

        lp = self.bitHopper.lp.lastBlock
        if lp == None:
            lp = {}
        else:
            lp = self.bitHopper.lp.blocks[lp]
        response = json.dumps({
            "current":self.bitHopper.pool.get_current(), 
            'mhash':self.bitHopper.speed.get_rate(), 
            'difficulty':self.bitHopper.difficulty.get_difficulty(),
            'ixc_difficulty':self.bitHopper.difficulty.get_ixc_difficulty(),
            'i0c_difficulty':self.bitHopper.difficulty.get_i0c_difficulty(),
            'nmc_difficulty':self.bitHopper.difficulty.get_nmc_difficulty(),
            'scc_difficulty':self.bitHopper.difficulty.get_scc_difficulty(),
            'block':self.bitHopper.lp.getBlocks(),
            'servers':self.bitHopper.pool.get_servers()})
        return response
