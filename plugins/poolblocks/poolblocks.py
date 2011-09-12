#License#
# poolblocks.py is created by echiu64 and licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
# http://creativecommons.org/licenses/by-nc-sa/3.0/
# Based on a work at github.com.
#
# Portions based on blockinfo.py by ryouiki and licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#

import eventlet
from eventlet.green import os, threading, socket
from eventlet import greenpool

import traceback
import random
import time
import sys
import re
import work

import operator

from peak.util import plugins
from ConfigParser import RawConfigParser

import blockexplorer

class PoolBlocks:
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.work = work.Work(self)
        self.refreshInterval = 300
        self.refreshRandomJitter = 90
        self.blocks = {}
        self.parseConfig()        
        self.threadpool = greenpool.GreenPool(size=8)
        self.execpoolsize = 20
        self.execpool = greenpool.GreenPool(size=self.execpoolsize)
        hook = plugins.Hook('plugins.lp.announce')
        hook.register(self.lp_announce)
        self.lock = threading.RLock()
        eventlet.spawn_n(self.run)
        
    def parseConfig(self):
        self.fetchconfig = RawConfigParser()
        self.fetchconfig.read('poolblock.cfg')
        try:
            self.refreshInterval = self.bitHopper.config.readint('poolblocks', 'refreshInterval')
            self.refreshRandomJitter = self.bitHopper.config.readint('poolblocks', 'refreshRandomJitter')
            self.execpoolsize = self.bitHopper.config.readint('poolblocks', 'execpoolsize')
        except:
            pass
                
    def log_msg(self,msg):
        self.bitHopper.log_msg(msg, cat='poolblock')
        
    def log_dbg(self,msg):
        self.bitHopper.log_dbg(msg, cat='poolblock')
        
    def log_trace(self,msg):
        self.bitHopper.log_trace(msg, cat='poolblock')

    def run(self):
        while True:
            # TODO
            try:
                self.fetchBlocks()
                self.execpool.waitall()
                self.threadpool.waitall()
                if self.bitHopper.options.trace:
                    self.report()
                interval = self.refreshInterval
                interval += random.randint(0, self.refreshRandomJitter)
                eventlet.sleep(interval)
            except Exception, e:
                traceback.print_exc()
                eventlet.sleep(30)
    
    def fetchBlocks(self):
        with self.lock:
            self.log_trace('fetchBlocks')
            for pool in self.fetchconfig.sections():
                self.log_trace('fetchBlocks: ' + str(pool))
                url = self.fetchconfig.get(pool, 'url')
                searchStr = self.fetchconfig.get(pool, 'search')
                try: mode = self.fetchconfig.get(pool, 'mode')
                except: mode = 'b'
                #interval = self.refreshInterval
                #interval += random.randint(0, self.refreshRandomJitter)
                #self.log_dbg(pool + ' fetch in ' + str(interval))
                self.execpool.spawn_n(self.fetchBlocksFromPool, pool, url, searchStr, mode)
            self.log_trace('waitall()')
            
    
    def fetchBlocksFromPool(self, pool, url, searchstr, mode='b'):
        self.log_trace('fetchBlockFromPool ' + str(pool) + ' | ' + str(url) + ' | ' + str(searchstr) + ' | ' + str(mode) )
        searchPattern = re.compile(searchstr)
        data = self.work.get(url)
        outputs = searchPattern.findall(data)
        matchCount = 0

        if mode == 'b':
            # pool reports block# solved
            #self.log_trace(str(outputs))
            for blockNumber in outputs:
                if blockNumber in self.blocks:
                    if self.blocks[blockNumber].owner != pool:
                        self.log_trace('[' + pool + '] block ' + str(blockNumber) + ' exists, setting owner')
                        self.blocks[blockNumber].owner = pool
                        matchCount += 1                        
                    else:
                        self.log_trace('[' + pool + '] block ' + str(blockNumber) + ' exists, owner already set to: ' + self.blocks[blockNumber].owner)
                else:
                    self.log_trace('[' + pool + '] block ' + str(blockNumber) + ' does not exist, adding')
                    self.threadpool.spawn_n(self.fetchBlockFromPool, pool, blockNumber, mode)
                
        elif mode == 'h':
            # pool reports block hash solved
            #self.log_trace(str(outputs))
            for blockHash in outputs:                
                found = False
                for blockNumber in self.blocks:
                    if str(blockHash) == self.blocks[blockNumber].hash:
                        if self.blocks[blockNumber].owner != pool:
                            self.log_trace('[' + pool + '] Found hash, setting owner to ' + str(pool))
                            self.blocks[blockNumber].owner = pool
                            matchCount += 1
                        else:
                            self.log_trace('[' + pool + '] block ' + str(blockNumber) + ' exists, owner already set to: ' + self.blocks[blockNumber].owner)
                        found = True
                        break
                if found == False:
                    self.log_trace('[' + pool + '] Hash not found, looking up block number')
                    self.threadpool.spawn_n(self.fetchBlockFromPool, pool, blockHash, mode)
                    
        elif mode == 'g':
            # pool uses transaction id
            #self.log_trace(str(outputs))
            for txid in outputs:
                found = False
                for blockNumber in self.blocks:
                    #print txid + '/' + str(self.blocks[blockNumber].txid)
                    if str(txid) == self.blocks[blockNumber].txid:
                        if self.blocks[blockNumber].owner != pool:
                            self.log_trace('[' + pool + '] Found TXID, setting owner to ' + str(pool))
                            self.blocks[blockNumber].owner = pool
                            matchCount += 1                                                       
                        else:
                            self.log_trace('[' + pool + '] Found TXID, owner aready set to ' + str(pool))
                        found = True
                        break
                if found == False:
                    self.log_trace('[' + pool + '] TXID not found, looking up block number and hash')
                    self.threadpool.spawn_n(self.fetchBlockFromPool, pool, txid, mode)               
        
        #print('Infofetch - {0}>>> parsed {1} blocks > {2} matches'.format(self.poolName, len(outputs), matchCount))

    def fetchBlockFromPool(self, pool, blockInfo, mode='b'):
        self.log_trace('fetchBlockFromPool: ' + str(pool) + ' blockInfo ' + str(blockInfo))
        if mode == 'b':
            # block number
            blockNumber = blockInfo
            blockHash = blockexplorer.getBlockHashByNumber(self.bitHopper, blockNumber)
            if blockHash != None:
                self.blocks[blockNumber] = Block()
                self.blocks[blockNumber].owner = pool
                self.blocks[blockNumber].hash = blockHash
                hook = plugins.Hook('plugins.poolblocks.verified')
                hook.notify(blockNumber, blockHash, pool)
            else:
                self.log_msg('[' + pool + '] ERROR ' + str(blockNumber) + ' and hash ' + str(blockHash))
           
        elif mode == 'h':
            # block hash
            blockHash = blockInfo
            blockNumber = blockexplorer.getBlockNumberByHash(self.bitHopper, blockHash)
            self.log_dbg('[' + pool + '] Block Number ' + str(blockNumber) + ' found for hash ' + blockHash)
            if blockNumber != None:
                self.log_trace('[' + pool + '] Creating new block: ' + str(blockNumber))
                self.blocks[blockNumber] = Block()
                self.blocks[blockNumber].hash = blockHash
                self.blocks[blockNumber].owner = pool
                hook = plugins.Hook('plugins.poolblocks.verified')
                hook.notify(blockNumber, blockHash, pool)
            else:
                self.log_msg('[' + pool + '] ERROR ' + str(blockNumber) + ' and hash ' + str(blockHash))

        elif mode == 'g':
            # txid
            blockHash, blockNumber = blockexplorer.getBlockHashAndNumberByTxid(self.bitHopper, blockInfo)
            self.log_dbg('[' + pool + '] Block Number ' + str(blockNumber) + ' and hash ' + str(blockHash) + ' found for txid ' + blockInfo)
            if blockNumber != None and blockHash != None:
                found = False
                for bNumber in self.blocks:
                    if str(bNumber) == blockNumber:
                        self.log_dbg('['+pool+'] Found block ' + str(bNumber) + ' setting new owner')
                        self.blocks[blockNumber].owner = pool
                        self.blocks[blockNumber].txid = blockInfo
                        found = True
                        hook = plugins.Hook('plugins.poolblocks.verified')
                        hook.notify(blockNumber, blockHash, pool)
                        
                if found == False:
                    self.log_trace('[' + pool + '] Creating new block: ' + str(blockNumber))
                    self.blocks[blockNumber] = Block()
                    self.blocks[blockNumber].hash = blockHash
                    self.blocks[blockNumber].owner = pool
                    self.blocks[blockNumber].txid = blockInfo                    
                    hook = plugins.Hook('plugins.poolblocks.verified')
                    hook.notify(blockNumber, blockHash, pool)
            else:
                self.log_msg('[' + pool + '] ERROR ' + str(blockNumber) + ' and hash ' + str(blockHash))

    def report(self):
        self.log_trace('report()')
        keys = sorted(self.blocks.keys(), key=int)
        count = 0
        for blockNumber in keys:
            block = self.blocks[blockNumber]
            print "Block %6d %12s %64s " % ( int(blockNumber), str(block.owner), str(block.hash) )
        
    def lp_announce(self, lpobj, body, server, blockHash):
        # TODO
        pass
    
# class for Block       
class Block:
    def __init__(self):
        self.hash = None
        self.number = None
        self.owner = None
        self.coinbase = None #TBD
        self.txid = None #TBD
    
