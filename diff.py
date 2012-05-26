#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net


import threading, gevent
from btcnet_wrapper import btcnet_info
from collections import defaultdict
import logging
    
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
        self.diff = defaultdict(lambda: 10**6, self.diff)

        self.lock = threading.RLock()
        gevent.spawn(self.update_difficulty)

    def __getitem__(self, key):
        with self.lock:
            return self.diff.get(key, 10**6)

    def update_difficulty(self):
        while True:
            with self.lock:
                for coin in btcnet_info.get_coins():
                    if getattr(coin, 'difficulty', None):
                        try:
                            logging.info('Difficulty for %s:%s' % (coin.name, coin.difficulty))
                            self.diff[coin.name] = float(coin.difficulty)
                        except:
                            pass
            gevent.sleep(60)
