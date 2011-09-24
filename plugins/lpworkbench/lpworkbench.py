from eventlet.green import os, socket
import json
import sys
import webob
import time

from time import strftime
from peak.util import plugins

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
                    if block is not None and '_owner' in block:
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
        hook = plugins.Hook('plugins.blockaccuracy.report')
        hook.register(self.updateAccuracyData)
        self.poolAccuracy = None        

    def handle(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/json')])

        lp = self.bitHopper.lp.lastBlock
        if lp is None:
            lp = {}
        else:
            lp = self.bitHopper.lp.blocks[lp]
        
        # sort blocks by time
        blocks = self.bitHopper.lp.getBlocks()
        block_times = []
        for block in blocks:
            block_times.append(blocks[block]['_time'])
        
        block_times.sort()
        sorted_blocks = []
        for i in block_times:
            for block in blocks:
                if blocks[block]['_time'] == i:
                    tempblock = blocks[block]
                    del tempblock['_time']
                    time_str = strftime('%d-%b %H:%M:%S', i)
                    tempblock['_time'] = time_str
                    #sorted_blocks[block]['_time'] = time_str
                    sorted_blocks.append( {block:tempblock} )
                    break
                
        # filter accuracy data
        filterdAccuracy = {}
        if self.poolAccuracy is not None:
            for pool in self.poolAccuracy:
                hits = self.poolAccuracy[pool]['hit']
                incorrect = self.poolAccuracy[pool]['incorrect']
                total = self.poolAccuracy[pool]['total']
                if hits == 0 and incorrect == 0 and total == 0:
                    continue
                else:
                    filterdAccuracy[pool] = self.poolAccuracy[pool]
        
        response = json.dumps({
            "current":self.bitHopper.pool.get_current(), 
            'mhash':self.bitHopper.speed.get_rate(), 
            'difficulty':self.bitHopper.difficulty.get_difficulty(),
            'ixc_difficulty':self.bitHopper.difficulty.get_ixc_difficulty(),
            'i0c_difficulty':self.bitHopper.difficulty.get_i0c_difficulty(),
            'nmc_difficulty':self.bitHopper.difficulty.get_nmc_difficulty(),
            'scc_difficulty':self.bitHopper.difficulty.get_scc_difficulty(),
            'block':sorted_blocks,
            'accuracy':filterdAccuracy,
            'servers':self.bitHopper.pool.get_servers()})
        return response

    def updateAccuracyData(self, poolVerifiedData):
        #self.bitHopper.log_trace('updateAccuracyData: ' + str(poolVerifiedData) + ' / ' + str(len(poolVerifiedData)), cat='lpworkbench')
        self.poolAccuracy = poolVerifiedData
        