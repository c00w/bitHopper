#License#
#bitHopper by Colin Rice is licensed under a 
#Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import eventlet
from eventlet.green import os

import importlib

class Plugin():
    """Class which loads plugins from folders in the plugins folder."""
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.load_cfg()
        self.load_plugins()
        

    def load_cfg(self):
        """Load all config files from plugin directory"""
        self.bitHopper.log_msg('Loading Config Files')
        pool_configs = []
        for dirpath, dirnames, filenames in os.walk('plugins'):
            for name in filenames:
                try:
                    if name.split('.')[-1] == 'cfg':
                        pool_configs.append(os.path.join(dirpath, name))
                except Exception, e:
                    print e
        self.bitHopper.pool.pool_configs += pool_configs
        self.bitHopper.pool.loadConfig()

    def load_plugins(self):
        """Tries to load all plugins in folder plugins"""
        self.bitHopper.log_msg('Loading Plugins')      
        possible_plugins = os.listdir('plugins')
        for item in possible_plugins:
            if os.path.isdir(item):
                try:
                    module = importlib.import_module('plugins.' + str(item))
                    bithop_attr = getattr(self.bitHopper, item, None)
                    if bithop_attr is not None:
                        self.bitHopper.log_msg('Plugin name conflict: ' + str(item))
                        continue
                    
                    #Actually call module and store it in bitHopper
                    return_value = module.main(self.bitHopper)
                    if return_value is None:
                        setattr(self.bitHopper, item, module)
                    else:
                        setattr(self.bitHopper, item, return_value)
                except Exception, e:
                    self.bitHopper.log_msg("Error loading plugin: " + item)
                    self.bitHopper.log_msg(e)

