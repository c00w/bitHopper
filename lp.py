#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import work
import json
import exceptions
import time

from twisted.internet import reactor, defer

class LongPoll():
    def __init__(self,bitHopper):
        self.bitHopper = bitHopper
        self.pool = self.bitHopper.pool
        self.blocks = {}
        self.lastBlock = None
        self.errors = {}
        self.polled = {}

    def set_owner(self,server):
        if self.lastBlock != None:
            self.blocks[self.lastBlock]["_owner"] = server
            self.bitHopper.log_msg('Setting Block Owner :' + str(self.lastBlock))

    def get_owner(self):
        if self.lastBlock != None:
            return self.blocks[self.lastBlock]["_owner"]
        return ""

    def start_lp(self):
        for server in self.pool.servers:
            info = self.pool.servers[server]
            if info['role'] not in ['mine','mine_charity','mine_deepbit','info', 'backup','backup_latehop']:
                continue
            if info['lp_address'] != None:
                self.pull_lp(info['lp_address'],server)
            else:
                reactor.callLater(0, self.pull_server, server)
                
                
    def pull_server(self,server):
        #self.bitHopper.log_msg('Pulling from ' + server)
        server = self.pool.servers[server]
        work.jsonrpc_call(self.bitHopper.json_agent, server, [], self.bitHopper)

    def receive(self, body, server):
        self.polled[server] -= 1
        info = self.bitHopper.pool.servers[server]
        if info['role'] in ['mine_nmc','disable']:
            return
        if body == None:
            if server not in self.errors:
                self.errors[server] = 0
            self.errors[server] += 1
            #timeout? Something bizarre?
            if self.errors[server] < 3 and self.polled[server] == 0:
                self.bitHopper.reactor.callLater(0,self.pull_lp, (self.pool.servers[server]['lp_address'],server))
            return
        self.bitHopper.log_msg('received lp from: ' + server)
        try:
            response = json.loads(body)
            work = response['result']
            data = work['data']
            block = data[8:72]
            #block = int(block, 16)
            if block not in self.blocks:
                self.bitHopper.log_msg('New Block: ' + str(block))
                self.bitHopper.log_msg('Block Owner ' + server)
                self.blocks[block] = {}
                self.bitHopper.lp_callback(work)
                self.blocks[block]["_owner"] = server
                self.lastBlock = block

            self.blocks[block][server] = time.time()
        except Exception, e:
            self.bitHopper.log_dbg('Error in LP' + str(server) + str(body))
            self.bitHopper.log_dbg(e)
            if server not in self.errors:
                self.errors[server] = 0
            self.errors[server] += 1
            #timeout? Something bizarre?
            if self.errors[server] < 3 and self.polled[server] == 0:
                self.bitHopper.reactor.callLater(0,self.pull_lp, (self.pool.servers[server]['lp_address'],server))
            return
        if self.polled[server] == 0:
            self.bitHopper.reactor.callLater(0,self.pull_lp, (self.pool.servers[server]['lp_address'],server))
        
    def clear_lp(self,):
        pass

    def check_lp(self,server):
        return self.pool.get_entry(server)['lp_address']  == None

    def set_lp(self,url,server):
        #self.bitHopper.log_msg('set_lp ' + url + ' ' + server)
        try:
            info = self.bitHopper.pool.get_entry(server)
            if info['lp_address'] == url:
                return
            info['lp_address'] = url
            self.bitHopper.reactor.callLater(0,self.pull_lp, (url,server))
        except Exception,e:
            self.bitHopper.log_msg('set_lp error')
            self.bitHopper.log_dbg(str(e))

    def pull_lp(self,(url,server)):
        #self.bitHopper.log_msg('pull_lp ' + url + ' ' + server)
        pool = self.pool.servers[server]
        if url[0] == '/':
            lp_address = str(pool['mine_address']) + str(url)
        else:
            lp_address = str(url)
        self.bitHopper.log_msg("LP Call " + lp_address)
        try:
            if server not in self.polled:
                self.polled[server] = 0
            self.polled[server] += 1
            if self.polled[server] ==1:
                d = work.jsonrpc_lpcall(self.bitHopper.get_lp_agent(),server, lp_address, self)
                d.addErrback(self.bitHopper.log_dbg)
            else:
                self.polled[server] -= 1
        except Exception,e :
            self.bitHopper.log_dbg('pull_lp error')
            self.bitHopper.log_dbg(e)
