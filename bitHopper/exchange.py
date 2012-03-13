#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

import gevent, logging
import threading
from ConfigParser import NoOptionError
import diff

from btcnet_wrapper import btcnet_info

class Exchange():
    "Pulls Exchange rates, updates them and calculates profitability"
    
    def __init__(self, bitHopper, difficulty):
        self.bitHopper = bitHopper
        self.difficulty = difficulty
        try: 
            self.calculate_profit = bitHopper.config.getboolean('main', 'calculate_profit')
        except NoOptionError: 
            self.calculate_profit = True
            
        self.lock = threading.RLock()
        self.rate = {'btc':1.0}
        self.profitability = {'btc':1.0}
        
        gevent.spawn(self.update_profitability)

    def calc_profit(self):
        with self.lock:
            btc_diff = self.difficulty.diff['btc']
            for coin in self.rate:
                if self.calculate_profit == True:
                    if coin not in self.difficulty.diff:
                        continue
                    diff = self.bitHopper.difficulty.diff[coin]
                    self.profitability[coin] = (float(btc_diff) / diff * self.rate[coin])
                else: 
                    self.profitability[coin] = 1.0
            self.rate['btc'] = 1.0

    def update_profitability(self):
        while True:
            with self.lock:
                for coin in btcnet_info.get_coins():
                    self.rate[coin.name] = getattr(coin, 'exchange', 0)
                self.calc_profit()
            gevent.sleep(60*5)
