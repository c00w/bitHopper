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
        self.btc_difficulty = 1755425.3203287
        self.nmc_difficulty = 94037.96
        self.ixc_difficulty = 16384
        self.i0c_difficulty = 1372
        self.scc_difficulty = 5354
        self.lock = threading.RLock()
        eventlet.spawn_n(self.update_difficulty)
        self.diff = {'btc':1755425.3203287, 'nmc':94037.96, 'ixc':16384, 'i0c':1372, 'scc':5354}

    def get_difficulty(self):
        return self.btc_difficulty
    
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
            #timeout = eventlet.timeout.Timeout(5, Exception(''))
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
            self.diff[diff_attr[0:3]] = float(output)
            self.bitHopper.log_dbg('Retrieved Difficulty: ' + str(self.__dict__[diff_attr]))
        except Exception, e:
            self.bitHopper.log_dbg('Unable to update difficulty for ' + coin + ': ' + str(e))
        finally:
            #timeout.cancel()
            pass

    def update_difficulty(self):
        while True:
            "Tries to update difficulty from the internet"
            with self.lock:
                
                self.updater("Bitcoin", 'http://blockexplorer.com/q/getdifficulty', 'btc_difficulty')
                self.updater("Namecoin", 'http://namecoinpool.com/', 'nmc_difficulty', "Current difficulty:</td><td>([.0-9]+)</td>")
                self.updater("SolidCoin", 'http://allchains.info', 'scc_difficulty', "<td> sc </td><td align=\'right\'> ([0-9]+)")
                self.updater("IXcoin", 'http://allchains.info', 'ixc_difficulty', "ixc </td><td align='right'> ([0-9]+) </td><td align='right'>   [.0-9]+ </td>")
                self.updater("I0coin", 'http://allchains.info', 'i0c_difficulty', "i0c </td><td align='right'> ([0-9]+) </td><td align='right'>   [.0-9]+ </td>")
            eventlet.sleep(60*10)
