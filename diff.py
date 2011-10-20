#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import re
import eventlet
from eventlet.green import threading, socket, urllib2
import ConfigParser

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
        self.gg_difficulty = 30
        cfg = ConfigParser.ConfigParser()
        cfg.read(["diffwebs.cfg"])
        self.diff_sites = []
        for site in cfg.sections():
             self.diff_sites.append(dict(cfg.items(site)))
        self.lock = threading.RLock()
        eventlet.spawn_n(self.update_difficulty)
        self.diff = {'btc': self.btc_difficulty, 'nmc': self.nmc_difficulty, 'ixc': self.ixc_difficulty, 'i0c': self.i0c_difficulty, 'scc': self.scc_difficulty, 'gg': self.gg_difficulty}

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

    def updater(self, coin, short_coin):
        # Generic method to update the difficulty of a given currency
        self.bitHopper.log_msg('Updating Difficulty of ' + coin)
        config_diffcoin = [site for site in self.diff_sites if site['coin'] == short_coin]
        #timeout = eventlet.timeout.Timeout(5, Exception(''))
        useragent = {'User-Agent': self.bitHopper.config.get('main', 'work_user_agent')}
        for site in config_diffcoin:
            try:
                req = urllib2.Request(site['url'], headers = useragent)
                response = urllib2.urlopen(req)
                if site['get_method'] == 'direct': 
                    output = response.read()
                elif site['get_method'] == 'regexp':
                    diff_str = response.read()
                    output = re.search(site['pattern'], diff_str)
                    output = output.group(1)
                elif site['get_method'] == 'json':
                    pass
                self.__dict__[short_coin + '_difficulty'] = float(output)
                self.diff[short_coin] = float(output)
                self.bitHopper.log_dbg('Retrieved Difficulty: ' + str(self.__dict__[short_coin + '_difficulty']))
                break
            except Exception, e:
                self.bitHopper.log_dbg('Unable to update difficulty for ' + coin + ' from ' + site['url'] + ' : ' + str(e))
            finally:
                #timeout.cancel()
                pass

    def update_difficulty(self):
        while True:
            "Tries to update difficulty from the internet"
            with self.lock:
                
                self.updater("Bitcoin", 'btc')
                self.updater("Namecoin", 'nmc')
                self.updater("SolidCoin", 'scc')
                self.updater("IXcoin", 'ixc')
                self.updater("I0coin", 'i0c')
            eventlet.sleep(60*10)
