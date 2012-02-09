#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.


import threading, gevent
from btcnet_wrapper import btcnet_info
    
    
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

        self.lock = threading.RLock()
        gevent.spawn(self.update_difficulty)

    def __getitem__(self, key):
        with self.lock:
            return self.diff[key]

    def update_difficulty(self):
        while True:
            with self.lock:
                for coin in btcnet_info.get_coins():
                    if getattr(coin, 'difficulty', None):
                        self.diff[coin.name] = float(coin.difficulty)
            gevent.sleep(60*10)
