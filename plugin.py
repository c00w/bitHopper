#License#
#bitHopper by Colin Rice is licensed under a 
#Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import eventlet
from eventlet.green import os



class Plugin():
    """Class which loads plugins from folders in the plugins folder."""
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        pool_configs = []
        for dirpath, dirnames, filenames in os.walk('plugins'):
            for name in filenames:
                try:
                    if name.split('.')[1] == 'cfg':
                        pool_configs.append(os.path.join(dirpath, name))
                except Exception, e:
                    print e
        self.bitHopper.pool.pool_configs += pool_configs
        self.bitHopper.pool.loadConfig()
                
                
            
