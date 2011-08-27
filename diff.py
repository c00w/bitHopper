#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import urllib2
import re
import eventlet
from eventlet.green import threading

class Difficulty():
    "Stores difficulties and automaticlaly updates them"
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.difficulty = 1805700.8361937
        self.nmc_difficulty = 94037.96
        self.ixc_difficulty = 16384
        self.i0c_difficulty = 4096
        self.scc_difficulty = 13970
        self.lock = threading.RLock()
        eventlet.spawn_n(self.update_difficulty)

    def get_difficulty(self):
        with self.lock:
            return self.difficulty
    
    def get_nmc_difficulty(self):
        with self.lock:
            return self.nmc_difficulty

    def get_ixc_difficulty(self):
        with self.lock:
            return self.ixc_difficulty
    
    def get_i0c_difficulty(self):
        with self.lock:
            return self.i0c_difficulty

    def get_scc_difficulty(self):
        with self.lock:
            return self.scc_difficulty

    def update_difficulty(self):
        while True:
            "Tries to update difficulty from the internet"
            with self.lock:
                self.bitHopper.log_msg('Updating Difficulty')
                try:
                    req = urllib2.Request('http://blockexplorer.com/q/getdifficulty')
                    response = urllib2.urlopen(req)
                    diff_string = response.read()
                    self.difficulty = float(diff_string)
                    self.bitHopper.log_dbg('Retrieved Difficulty:' + str(diff_string))
                except:
                    pass
                
                self.bitHopper.log_msg('Updating NameCoin Difficulty')
                try:
                    req = urllib2.Request('http://namebit.org/')
                    response = urllib2.urlopen(req)
                    diff_str = response.read()
                    output = re.search('<td id="difficulty">([.0-9]+)</td>', diff_str)
                    output = output.group(1)
                    self.nmc_difficulty = float(output)
                    self.bitHopper.log_dbg('Retrieved NameCoin Difficulty:' + str(self.nmc_difficulty))
                except:
                    pass
                    
                self.bitHopper.log_msg('Updating SolidCoin Difficulty')
                try:
                    req = urllib2.Request('http://sobtc.digbtc.net')
                    response = urllib2.urlopen(req)
                    diff_str = response.read()
                    output = re.search('difficulty: <b>([0-9]+)<', diff_str)
                    output = output.group(1)
                    self.scc_difficulty = float(output)
                    self.bitHopper.log_dbg('Retrieved SolidCoin Difficulty:' + str(self.scc_difficulty))
                except:
                    pass
            eventlet.sleep(60*60*6)
