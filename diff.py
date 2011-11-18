#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import re
import eventlet
from eventlet.green import threading, socket, urllib2
import ConfigParser
import functools

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class Difficulty():
    """
    Stores difficulties and automatically updates them
    Access difficulties by using this item as a dictionary
    """

    def __init__(self, bitHopper):
        """
        Sets up coin difficulties and reads in old difficulties
        from file.
        """

        #Add Coins
        self.diff = {}
        for attr_coin in bitHopper.altercoins.itervalues():
            self.diff[attr_coin['short_name']] = attr_coin['recent_difficulty']

        #Store bitHopper for logging
        self.bitHopper = bitHopper

        #Read in old diffs
        cfg = ConfigParser.ConfigParser()
        cfg.read(["diffwebs.cfg"])

        #Add diff_sites
        self.diff_sites = []
        for site in cfg.sections():
             self.diff_sites.append(dict(cfg.items(site)))

        self.lock = threading.RLock()
        eventlet.spawn_n(self.update_difficulty)

    def __getitem__(self, key):
        return self.diff[key]

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
                self.diff[short_coin] = float(output)
                self.bitHopper.log_dbg('Retrieved Difficulty: ' + str(self[short_coin]))
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
                output_diffs = ConfigParser.ConfigParser()
                output_diffs.read("whatevercoin.cfg")   
                for generic_title, attr_coin in self.bitHopper.altercoins.iteritems():
                    self.updater(attr_coin['long_name'], attr_coin['short_name'])
                    output_diffs.set(generic_title, 'recent_difficulty', self.diff[attr_coin['short_name']])
                output = open("whatevercoin.cfg", 'wb')
                output_diffs.write(output)
                output.close()
            eventlet.sleep(60*10)
