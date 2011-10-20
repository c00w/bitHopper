#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import re
import eventlet
from eventlet.green import threading, socket, urllib2
from ConfigParser import NoOptionError

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class Exchange():
    "Pulls Exchange rates, updates them and calculates profitability"
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        try: self.calculate_profit = bitHopper.config.getboolean('main', 'calculate_profit')
        except NoOptionError: self.calculate_profit = True
        self.lock = threading.RLock()
        eventlet.spawn_n(self.update_profitability)
        self.rate = {'btc':1.0}
        self.profitability = {'btc':1.0}
    

    def updater(self, coin, url_diff, reg_exp = None):
        # Generic method to update the exchange rate of a given currency
        self.bitHopper.log_msg('Updating Exchange Rate of ' + coin)
        if self.calculate_profit == True:
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
                self.rate[coin] = float(output)
                self.bitHopper.log_dbg('Retrieved Exchange rate for ' +str(coin) + ': ' + output)
            except Exception, e:
                self.bitHopper.log_dbg('Unable to update exchange rate for ' + coin + ': ' + str(e))
                self.rate[coin] = 0.0
            finally:
                #timeout.cancel()
                pass
        else: self.rate[coin] = 1.0

    def calc_profit(self):
        with self.lock:
            btc_diff = self.bitHopper.difficulty.diff['btc']
            for coin in self.rate:
                if self.calculate_profit == True:
                    if coin not in self.bitHopper.difficulty.diff:
                        continue
                    diff = self.bitHopper.difficulty.diff[coin]
                    self.profitability[coin] = (float(btc_diff) / diff * self.rate[coin])
                else: self.profitability[coin] = 1.0

    def update_profitability(self):
        while True:
            "Tries to update profit from the internet"
            with self.lock:
                for generic_title, market in self.bitHopper.altercoins.iteritems():
                    if market.has_key('site_exchange') and market.has_key('pattern_site_exchange'):
                        self.updater(market['long_name'], market['site_exchange'], market['pattern_site_exchange'])
                
                self.calc_profit()

    
            eventlet.sleep(60*5)
