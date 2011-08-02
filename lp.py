#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import work
import json
import exceptions
import time

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

    def receive(self, body, server):
        #self.bitHopper.log_msg('recieved lp from: ' + server['pool_index'])
        response = json.loads(body)
        work = response['params'][0]
        data = work['data']
        block = data[8:72]

        if block not in self.blocks:
            self.blocks[block] = {}
            self.bitHopper.lp_callback(work)

        self.blocks[block][server] = time.time()
        self.pull_lp(self.pool[server]['lp_address'],server)
        
    def clear_lp(self,):
        self.lp_set = False

    def check_lp(self,server):
        return self.pool.get_entry(server)['lp_address']  == None

    def set_lp(self,url,server):
        #self.bitHopper.log_msg('set_lp ' + url + ' ' + server)
        try:
            info = self.bitHopper.pool.get_entry(server)
            if info['lp_address'] == url:
                return
            info['lp_address'] = url
            self.pull_lp(url,server)
        except Exception,e:
            self.bitHopper.log_dbg('set_lp error')
            self.bitHopper.log_dbg(str(e))

    def pull_lp(self,url,server):
        #self.bitHopper.log_msg('pull_lp ' + url + ' ' + server)
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
