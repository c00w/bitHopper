#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import re
import eventlet
from eventlet.green import threading, socket, urllib2

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class Difficulty():
    "Stores difficulties and automaticlaly updates them"
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.difficulty = 1777774.4820015
        self.nmc_difficulty = 94037.96
        self.ixc_difficulty = 16384
        self.i0c_difficulty = 1372
        self.scc_difficulty = 5354
        self.lock = threading.RLock()
        eventlet.spawn_n(self.update_difficulty)

    def get_difficulty(self):
        return self.difficulty
    
    def get_nmc_difficulty(self):
        return self.nmc_difficulty

    def get_ixc_difficulty(self):
        return self.ixc_difficulty
    
    def get_i0c_difficulty(self):
        return self.i0c_difficulty
    
    def get_scc_difficulty(self):
        return self.scc_difficulty

    def updater(self, coin, url_diff, diff_attr, reg_exp = None):
        # Generic method to update the difficulty of a given currency
        self.bitHopper.log_msg('Updating Difficulty of ' + coin)
        try:
            useragent = {'User-Agent': self.bitHopper.config.get('main', 'work_user_agent')}
            req = urllib2.Request(url_diff, headers = useragent)
            response = urllib2.urlopen(req)
            if reg_exp == None: 
                output = response.read()
            else:
                diff_str = response.read()
                output = re.search(reg_exp, diff_str)
                output = output.group(1)
            self.__dict__[diff_attr] = float(output)
            self.bitHopper.log_dbg('Retrieved Difficulty: ' + str(self.__dict__[diff_attr]))
        except Exception, e:
            self.bitHopper.log_dbg('Unable to update difficulty for ' + coin + ': ' + str(e))

    def update_difficulty(self):
        while True:
            "Tries to update difficulty from the internet"
            with self.lock:
                self.updater("Bitcoin", 'http://blockexplorer.com/q/getdifficulty', 'difficulty')
                self.updater("Namecoin", 'http://namebit.org/', 'nmc_difficulty', '<td id="difficulty">([.0-9]+)</td>')
                self.updater("SolidCoin", 'http://solidcoin.whmcr.co.uk/chain/SolidCoin?count=1', 'scc_difficulty', '<td>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}</td><td>\d{1,}</td><td>[.0-9]+</td><td>([.0-9]+)</td>')
                self.updater("IXcoin", 'http://allchains.info', 'ixc_difficulty', "ixc </td><td align='right'> ([0-9]+) </td><td align='right'>   [.0-9]+ </td>")
                self.updater("I0coin", 'http://allchains.info', 'i0c_difficulty', "i0c </td><td align='right'> ([0-9]+) </td><td align='right'>   [.0-9]+ </td>")
            eventlet.sleep(60*60*6)
