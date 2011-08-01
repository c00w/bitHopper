#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import work
import json
import exceptions

from twisted.internet import reactor, defer

class LongPoll():
    def __init__(self,bithop):
        self.lp_set = False
        self.bitHopper = bithop
        self.pool = self.bitHopper.pool
        self.blocks = {}

    def start_lp(self):
        for server in self.pool:
            info = self.pool.servers(server)
            if info['lp_address'] != None:
                self.pull_lp(info['lp_address'],server)

    @defer.inlineCallbacks
    def update_lp(self,response, server):
        self.bitHopper.log_msg("LP triggered from server " + server)

        if response == None:
            defer.returnValue(None)

        try:
            finish = Deferred()
            response.deliverBody(work.WorkProtocol(finish))
            body = yield finish
        except Exception, e:
            self.bitHopper.log_msg('Reading LP Response failed')
            self.lp_set = True
            defer.returnValue(None)

        try:
            message = json.loads(body)
            value =  message['result']
            #defer.returnValue(value)
        except exceptions.ValueError, e:
            self.bitHopper.log_msg("Error in json decoding, Probably not a real LP response")
            self.lp_set = True
            self.bitHopper.log_dbg(body)
            defer.returnValue(None)

        self.pool.update_api_servers()
        current = self.bitHopper.get_server()
        self.bitHopper.select_best_server()
        if current == self.bitHopper.get_server():
            self.bitHopper.log_dbg("LP triggering clients manually")
            self.bitHopper.lp_callback()
            self.lp_set = False 
            
        defer.returnValue(None)

    def receive(self, body, server):
        response = json.loads(body)
        work = response['params'][0]

        self.pull_lp(self.pool[server]['lp_address'],server)
        
    def clear_lp(self,):
        self.lp_set = False

    def check_lp(self,server):
        return 'lp_address' in self.pool.get_server(server)

    def set_lp(self,url,server):

        info = self.bitHopper.pool.get_server(server)
        if info['lp_address'] == url:
            return
        info['lp_address'] = url
        self.pull_lp(url,server)

    def pull_lp(self,url,server):
        server = self.pool.servers[server]
        if url[0] == '/':
            lp_address = str(server['mine_address']) + str(url)
        else:
            lp_address = str(url)
        self.bitHopper.log_msg("LP Call " + lp_address)
        self.lp_set = True
        try:
            work.jsonrpc_lpcall(self.bitHopper.get_lp_agent(),server, lp_address, self)
        except Exception,e :
            self.bitHopper.log_dbg('pull_lp error')
            self.bitHopper.log_dbg(e)
