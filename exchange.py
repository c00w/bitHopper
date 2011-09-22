#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import re
import eventlet
from eventlet.green import threading, socket, urllib2

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class Exchange():
    "Pulls Exchange rates, updates them and calculates profitability"
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        
        self.lock = threading.RLock()
        eventlet.spawn_n(self.update_difficulty)
        self.rate = {'btc':1.0}
        self.profitability = {'btc':1.0}
    

    def updater(self, coin, url_diff, reg_exp = None):
        # Generic method to update the exchange rate of a given currency
        self.bitHopper.log_msg('Updating Exchange Rate of ' + coin)
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
        finally:
            #timeout.cancel()
            pass

    def calc_profit(self):
        with self.lock:
            btc_diff = self.bitHopper.difficulty.diff['btc']
            for coin in self.rate:
                if coin not in self.bitHopper.difficulty.diff:
                    continue
                diff = self.bitHopper.difficulty.diff[coin]
                self.profitability[coin] = (float(btc_diff)/diff*self.rate[coin])
        print self.profitability
                

    def update_difficulty(self):
        while True:
            "Tries to update difficulty from the internet"
            with self.lock:
                
                self.updater("ixc", 'http://ixchange.bitparking.com:8080/api/ticker', '\"average\":([0-9.]+)')
                self.updater("nmc", 'https://exchange.bitparking.com/main', "<th>Low:</th><td class=\"coin\">([0-9.]+)</td>")
                self.updater("scc", 'https://btc-e.com/sc_exchanger',  "Highest Bid Price<p><b><span id='max_price'>([0-9.]+)")
                self.updater("i0c", 'http://i0exchange.bitparking.com:8080/api/ticker', '\"average\":([0-9.]+)')

                self.calc_profit()

    
            eventlet.sleep(60*5)
