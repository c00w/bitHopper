#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import work
import json
import exceptions
import time
import threading

from twisted.internet import reactor, defer

def byteswap(value):
    bytes = []
    for i in xrange(0,len(value)):
        if i%2 == 1:
            bytes.append(value[i-1:i+1])
    return "".join(bytes[::-1])

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
            self.bitHopper.log_msg('Setting Block Owner ' + server+ ':' + str(self.lastBlock))

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
                self.pull_lp((info['lp_address'],server))
            else:
                reactor.callLater(0, self.pull_server, server)
                
                
    def pull_server(self,server):
        #self.bitHopper.log_msg('Pulling from ' + server)
        work.jsonrpc_call(self.bitHopper.json_agent, server, [], self.bitHopper)

    def receive(self, body, server):
        self.polled[server].release()
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
                if byteswap(block) in self.blocks:
                    block = byteswap(block)
                else:
                    self.bitHopper.log_msg('New Block: ' + str(block))
                    self.bitHopper.log_msg('Block Owner ' + server)
                    self.blocks[block] = {}
                    self.bitHopper.lp_callback(work)
                    self.blocks[block]["_owner"] = server
                    if self.bitHopper.pool.servers[server]['role'] == 'mine_deepbit':
                        self.bitHopper.pool.servers[server]['shares'] = 0
            if self.bitHopper.pool.servers[server]['role'] == 'mine_deepbit':
                self.lastBlock = block

            self.blocks[block][server] = time.time()
        except Exception, e:
            self.bitHopper.log_dbg('Error in LP' + str(server) + str(body))
            self.bitHopper.log_dbg(e)
            if server not in self.errors:
                self.errors[server] = 0
            self.errors[server] += 1
            #timeout? Something bizarre?
            if self.errors[server] > 3:
                return
        self.bitHopper.reactor.callLater(0,self.pull_lp, (self.pool.servers[server]['lp_address'],server))
        
    def clear_lp(self,):
        pass

    def check_lp(self,server):
        return self.pool.get_entry(server)['lp_address']  == None

    def set_lp(self,url,server):
        #self.bitHopper.log_msg('set_lp ' + url + ' ' + server)
        try:
            info = self.bitHopper.pool.get_entry(server)
            info['lp_address'] = url
            if server not in self.polled:
                self.polled[server] = threading.Semaphore()
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
        try:
            if self.polled[server].acquire(False):
                self.bitHopper.log_msg("LP Call " + lp_address)
                d = work.jsonrpc_lpcall(self.bitHopper.get_lp_agent(),server, lp_address, self)
                d.addErrback(self.bitHopper.log_dbg)
        except Exception,e :
            self.bitHopper.log_dbg('pull_lp error')
            self.bitHopper.log_dbg(e)
