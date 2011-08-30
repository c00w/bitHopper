#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import urllib2
import re
import eventlet
from eventlet.green import threading, socket

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

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

    def updater(self, coin, url_diff, diff_attr, reg_exp = None):
        # Generic method to update the difficulty of a given currency
        self.bitHopper.log_msg('Updating Difficulty of ' + coin)
        try:
            req = urllib2.Request(url_diff)
            response = urllib2.urlopen(req)
            if reg_exp == None: output = response.read()
            else:
                output = re.search('<td id="difficulty">([.0-9]+)</td>', diff_str)
                output = output.group(1)
            self.__dict__[diff_attr] = float(output)
            self.bitHopper.log_dbg('Retrieved Difficulty:' + str(self.__dict__[diff_attr]))
        except:
            pass

    def get_scc_difficulty(self):
        with self.lock:
            return self.scc_difficulty

    def update_difficulty(self):
        while True:
            "Tries to update difficulty from the internet"
            with self.lock:
                self.updater("Bitcoin", 'http://blockexplorer.com/q/getdifficulty', 'difficulty')
                self.updater("Namecoin", 'http://namebit.org/', 'nmc_difficulty', '<td id="difficulty">([.0-9]+)</td>')
                self.updater("SolidCoin", 'http://solidcoin.whmcr.co.uk/chain/SolidCoin?count=1', 'scc_difficulty', '<td>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}</td><td>\d{1,}</td><td>\d{1,}</td><td>([.0-9]+)</td>')
            eventlet.sleep(60*60*6)
