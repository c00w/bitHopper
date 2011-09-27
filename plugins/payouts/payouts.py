#!/usr/bin/python
#License#
# payouts.py by Cutmaster Flex and licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
# Based on a work at github.com.
#
# Usage: Add a unique wallet:xxxxx option for each pool to user.cfg
#        this will overwrite any previous manually set payout value

import traceback
from jsonrpc import ServiceProxy

import eventlet
from eventlet.green import time, threading

class Payouts():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.interval = 600
        self.parseConfig()
        self.log_msg(" - Payouts interval: " + str(self.interval))
        eventlet.spawn_n(self.run)
        self.lock = threading.RLock()
            
    def parseConfig(self):
        try:
            self.interval = self.bitHopper.config.getint('plugin.payouts', 'interval')
            self.rpcuser = self.bitHopper.config.get('plugin.payouts', 'rpcuser')
            self.rpcpass = self.bitHopper.config.get('plugin.payouts', 'rpcpass')
            self.rpchost = self.bitHopper.config.get('plugin.payouts', 'rpchost')
            self.rpcport = self.bitHopper.config.get('plugin.payouts', 'rpcport')
        except:
            traceback.print_exc()
        
    def log_msg(self, msg, **kwargs):
        self.bitHopper.log_msg(msg, cat='payouts')
        
    def log_dbg(self, msg, **kwargs):
        self.bitHopper.log_dbg(msg, cat='payouts')
        
    def run(self):
        access = ServiceProxy('http://' + self.rpcuser + ':' + self.rpcpass + '@' + self.rpchost + ':' + self.rpcport)
        while True:
            for server in self.bitHopper.pool.servers:
                info = self.bitHopper.pool.get_entry(server)

                if info['wallet'] != "":
                    wallet = info['wallet']
                    try:
                        getbalance = float(access.getreceivedbyaddress(wallet))
                        self.log_msg(server + ' ' + str(getbalance) + ' ' + wallet)
                        self.bitHopper.update_payout(server, float(getbalance))
                    except Exception e:
                        self.log_dbg("Error getting getreceivedbyaddress")
                        self.log_dbg(e)

            eventlet.sleep(self.interval)
