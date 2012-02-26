#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

import json, gevent, traceback, logging, gevent.coros
import time, threading, socket

from peak.util import plugins

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

def bytereverse(value):
    bytes = []
    for i in xrange(0,len(value)):
        if i%2 == 1:
            bytes.append(value[i-1:i+1])
    return "".join(bytes[::-1])

def wordreverse(in_buf):
    out_words = []
    for i in range(0, len(in_buf), 4):
        out_words.append(in_buf[i:i+4])
    out_words.reverse()
    out_buf = ""
    for word in out_words:
        out_buf += word
    return out_buf

class LongPoll():
    def __init__(self, bitHopper):
        hook_start = plugins.Hook('plugins.lp.init.start')
        hook_start.notify(self, bitHopper)
        self.bitHopper = bitHopper
        logging.info('LP Module Load')
        self.pool = self.bitHopper.pool
        self.blocks = {}
        self.lastBlock = None
        self.errors = {}
        self.polled = {}
        self.lock = threading.RLock()
        hook_end = plugins.Hook('plugins.lp.init.end')
        hook_end.notify(self, bitHopper)
        gevent.spawn(self.start_lp)

    # return all blocks data (excluding special "_defer" entry)
    def getBlocks(self):
        temp = {};
        for b in self.blocks:
            temp[b] = {}
            for v in self.blocks[b]:
                if v != "_defer":
                    temp[b][v] = self.blocks[b][v]
        return temp
    
    def set_owner(self, server, block = None):
        with self.lock:
            hook_start = plugins.Hook('plugins.lp.set_owner.start')
            hook_start.notify(self, server, block)

            if block == None:
                if self.lastBlock == None:
                    return
                block = self.lastBlock
            
            old_owner = self.blocks[block]["_owner"]
            if old_owner and self.pool.servers[server]['coin'] != self.pool.servers[old_owner]['coin']:
                return
            self.blocks[block]["_owner"] = server
            if server not in self.blocks[block]:
                self.blocks[block][server] = 0
            if '_defer' in self.blocks[block]:
                old_defer = self.blocks[block]['_defer']
            else:
                old_defer = None
            new_defer = gevent.coros.Semaphore()
            new_defer.acquire()
            self.blocks[block]['_defer'] = new_defer
            if old_defer:
                old_defer.release()
            logging.info('Setting Block Owner ' + server+ ':' + str(block))
            if server in self.bitHopper.pool.servers and self.bitHopper.pool.servers[server]['role'] == 'mine_lp' and old_owner != server:
                old_shares = self.bitHopper.pool.servers[server]['shares']
                self.bitHopper.pool.servers[server]['shares'] = 0
                self.bitHopper.scheduler.reset()
                self.bitHopper.select_best_server()
                gevent.spawn(self.api_check,server,block,old_shares)

            #If We change servers trigger a LP.
            if old_owner !=server:

                #Update list of valid server
                self.bitHopper.server_update()

                #Figure out which server to source work from
                source_server = self.bitHopper.pool.get_work_server()
                work, _, source_server, auth = self.bitHopper.work.jsonrpc_getwork(source_server, [])
                
                #Trigger the LP Callback with the new work.
                self.bitHopper.lp_callback.new_block(work, source_server, auth) 

            hook_end = plugins.Hook('plugins.lp.set_owner.end')
            hook_end.notify(self, server, block)

    def get_owner(self):
        with self.lock:
            if self.lastBlock != None:
                return self.blocks[self.lastBlock]["_owner"]
            return ""

    def start_lp(self):
        while True:
            # Loop Through each server and either call pull_lp with the address or
            # Do a getwork.
            
            for server in self.pool.get_servers():
                info = self.pool.servers[server]
                if info['role'] not in ['mine','mine_charity','mine_lp','backup','backup_latehop']:
                    continue
                if info['lp_address'] != None:
                    self.pull_lp(info['lp_address'],server)
                else:
                    gevent.spawn(self.pull_server, server)
            gevent.sleep(60*60)
                
                
    def pull_server(self, server):
        # A helper function so that we can have this in a different call.
        self.bitHopper.work.jsonrpc_call(server, [])

    def api_check(self, server, block, old_shares):
        with self.blocks[block]['_defer']:
            if self.blocks[block]['_owner'] != server:
                self.bitHopper.pool.servers[server]['shares'] += old_shares
                self.bitHopper.select_best_server()

    def add_block(self, block, work, server, auth):
        """ Adds a new block. server must be the server the work is coming from """
        with self.lock:
            hook_start = plugins.Hook('plugins.lp.add_block.start')
            try:
                hook_start.notify(self, block, work, server)
            except:
                traceback.print_exc()
            self.blocks[block]={}
            self.blocks[block]['_time'] = time.localtime()
            #Dump merkle roots
            self.bitHopper.getwork_store.drop_roots()
            #Trigger LP
            self.bitHopper.lp_callback.new_block(work, server, auth)
            self.blocks[block]["_owner"] = None
            self.lastBlock = block
        hook_end = plugins.Hook('plugins.lp.add_block.end')
        hook_end.notify(self, block, work, server)

    def receive(self, body, server, auth):
        hook_start = plugins.Hook('plugins.lp.receive.start')
        hook_start.notify(self, body, server)
        if server in self.polled:
            self.polled[server].release()
        logging.debug('received lp from: ' + server)
        logging.log(0, 'LP: ' + str(body))
        info = self.bitHopper.pool.servers[server]
        if info['role'] in ['disable', 'info']:
            return
        if body == None:
            logging.debug('error in long poll from: ' + server)
            with self.lock:
                if server not in self.errors:
                    self.errors[server] = 0
                self.errors[server] += 1
            #timeout? Something bizarre?
            if self.errors[server] < 3 or info['role'] == 'mine_lp':
                gevent.sleep(1)
                gevent.spawn(self.pull_lp, self.pool.servers[server]['lp_address'],server, False)
            return
        try:
            output = True
            response = json.loads(body)
            work = response['result']
            data = work['data']

            block = data.decode('hex')[0:64]
            block = wordreverse(block)
            block = block.encode('hex')[56:120]
            #block = int(block, 16)

            with self.lock:
                if block not in self.blocks:
                    logging.info('New Block: ' + str(block))
                    logging.info('Block Owner ' + server)
                    self.add_block(block, work, server, auth)

            #Add the lp_penalty if it exists.
            with self.lock:
                offset = self.pool.servers[server].get('lp_penalty','0')
                self.blocks[block][server] = time.time() + float(offset)
                logging.debug('EXACT ' + str(server) + ': ' + str(self.blocks[block][server]))
                if self.blocks[block]['_owner'] == None or self.blocks[block][server] < self.blocks[block][self.blocks[block]['_owner']]:
                    self.set_owner(server,block)
                    hook_announce = plugins.Hook('plugins.lp.announce')
                    logging.debug('LP Notify')
                    hook_announce.notify(self, body, server, block)
        
            hook_start = plugins.Hook('plugins.lp.receive.end')
            hook_start.notify(self, body, server, block)

        except Exception, e:
            output = False
            logging.debug('Error in Long Poll ' + str(server) + str(body))
            if self.bitHopper.options.debug:
                traceback.print_exc()
            if server not in self.errors:
                self.errors[server] = 0
            with self.lock:
                self.errors[server] += 1
            #timeout? Something bizarre?
            if self.errors[server] > 3 and info['role'] != 'mine_lp':
                return
        gevent.spawn_later(0, self.pull_lp, self.pool.servers[server]['lp_address'],server,output)
        
    def clear_lp(self,):
        pass

    def check_lp(self,server):
        return self.pool.get_entry(server)['lp_address']  == None

    def set_lp(self,url,server):
        #logging.info('set_lp ' + url + ' ' + server)
        try:
            info = self.bitHopper.pool.get_entry(server)
            info['lp_address'] = url
            if server not in self.polled:
                self.polled[server] = gevent.coros.Semaphore()
            gevent.spawn(self.pull_lp, url,server)
        except Exception, e:
            logging.info('set_lp error')
            logging.info(e)

    def pull_lp(self,url,server, output = True):
        #logging.info('pull_lp ' + url + ' ' + server)
        if url == None or server not in self.pool.servers:
            return
        pool = self.pool.servers[server]
        if url[0] == '/':
            lp_address = str(pool['mine_address']) + str(url)
        else:
            lp_address = str(url)
        if lp_address[0:7] != 'http://':
            lp_address = "http://" + lp_address
        try:
            if self.polled[server].acquire(False):
                if output or self.bitHopper.options.debug:
                    logging.info("Long Poll Call " + lp_address)
                else:
                    logging.debug("Long Poll Call " + lp_address)
                self.bitHopper.work.jsonrpc_lpcall(server, lp_address, self)
        except Exception, e :
            logging.debug('pull_lp error')
            logging.debug(e)
