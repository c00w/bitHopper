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
            if '_defer' in self.blocks[self.lastBlock]:
                self.blocks[self.lastBlock]['_defer'].callback(server)
            self.bitHopper.log_msg('Setting Block Owner ' + server+ ':' + str(self.lastBlock))

    def get_owner(self):
        if self.lastBlock != None:
            return self.blocks[self.lastBlock]["_owner"]
        return ""

    def start_lp(self):
        # Loop Through each server and either call pull_lp with the address or
        # Do a getwork.
        for server in self.pool.servers:
            info = self.pool.servers[server]
            if info['role'] not in ['mine','mine_charity','mine_deepbit','info', 'backup','backup_latehop']:
                continue
            if info['lp_address'] != None:
                self.pull_lp(info['lp_address'],server)
            else:
                reactor.callLater(0, self.pull_server, server)
                
                
    def pull_server(self,server):
        # A helper function so that we can have this in a different call.
        work.jsonrpc_call(self.bitHopper.json_agent, server, [], self.bitHopper)

    def lp_api(self,server,block):
	print "lp_api call for " + str(server) + " - " + block
        old_shares = self.bitHopper.pool.servers[server]['shares']
        self.bitHopper.pool.servers[server]['shares'] = 0
        self.bitHopper.select_best_server()
        ######## This is throwing a bunch of errors
        if '_defer' not in self.blocks[block]:
            self.blocks[block]['_defer'] = defer.Deferred()
        self.blocks[block]['_defer'].addCallback(self.api_check,server,block,old_shares)

    def api_check(self, server, block, old_shares):
        if self.blocks[block]['_owner'] != server:
            self.bitHopper.pool.servers[server]['shares'] += old_shares
            self.bitHopper.select_best_server()

    def receive(self, body, server):
        self.polled[server].release()
        self.bitHopper.log_dbg('received lp from: ' + server)
        info = self.bitHopper.pool.servers[server]
        if info['role'] in ['mine_nmc','disable','mine_ixc']:
            return
        if body == None:
            self.bitHopper.log_dbg('error in lp from: ' + server)
            if server not in self.errors:
                self.errors[server] = 0
            self.errors[server] += 1
            #timeout? Something bizarre?
            if self.errors[server] < 3 or info['role'] == 'mine_deepbit':
                self.bitHopper.reactor.callLater(0,self.pull_lp, self.pool.servers[server]['lp_address'],server, False)
            return
        try:
            output = True
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
                    self.blocks[block]={}
                    self.bitHopper.lp_callback(work)
                    self.blocks[block]["_owner"] = server
                    if self.bitHopper.lpBot != None:
                        self.bitHopper.lpBot.announce(str(server), str(block))
                    else:
                        if self.bitHopper.pool.servers[server]['role'] == 'mine_deepbit':
                            self.lp_api(server, block)
                        
            if self.bitHopper.pool.servers[server]['role'] == 'mine_deepbit':
                self.lastBlock = block

            #Add the lp_penalty if it exists.
            offset = self.pool.servers[server].get('lp_penalty','0')
            self.blocks[block][server] = time.time() + float(offset)
            if self.blocks[block][server] < self.blocks[block][self.blocks[block]['_owner']]:
                self.blocks[block]['_owner'] = server
        except Exception, e:
            output = False
            self.bitHopper.log_dbg('Error in LP ' + str(server))
            self.bitHopper.log_dbg(e)
            if server not in self.errors:
                self.errors[server] = 0
            self.errors[server] += 1
            #timeout? Something bizarre?
            if self.errors[server] > 3 and info['role'] != 'mine_deepbit':
                return
        self.bitHopper.reactor.callLater(0,self.pull_lp, self.pool.servers[server]['lp_address'],server,output)
        
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
            self.bitHopper.reactor.callLater(0,self.pull_lp, url,server)
        except Exception,e:
            self.bitHopper.log_msg('set_lp error')
            self.bitHopper.log_dbg(str(e))

    def pull_lp(self,url,server, output = True):
        #self.bitHopper.log_msg('pull_lp ' + url + ' ' + server)
        pool = self.pool.servers[server]
        if url[0] == '/':
            lp_address = str(pool['mine_address']) + str(url)
        else:
            lp_address = str(url)
        try:
            if self.polled[server].acquire(False):
                if output:
                    self.bitHopper.log_msg("LP Call " + lp_address)
                else:
                    self.bitHopper.log_dbg("LP Call " + lp_address)
                work.jsonrpc_lpcall(self.bitHopper.get_lp_agent(),server, lp_address, self)
        except Exception,e :
            self.bitHopper.log_dbg('pull_lp error')
            self.bitHopper.log_dbg(e)
