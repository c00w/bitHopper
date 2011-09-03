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
                    self.bitHopper.log_msg("Unable to load config file for:\n%s \n\n%s") % (dirpath, e)
        self.bitHopper.pool.pool_configs += pool_configs
        self.bitHopper.pool.loadConfig()

    def load_plugins(self):
        """Tries to load all plugins in folder plugins"""
        config = self.bitHopper.config
        if config.get('pluginmode', 'mode').find('disabled') == -1:
            self.bitHopper.log_msg('Loading Plugins')
            possible_plugins = os.listdir('plugins')

            if config.get('pluginmode', 'mode').find('auto') > -1:
                autoMode = True
            else:
                autoMode = False

            for item in possible_plugins:
                if os.path.isdir(os.path.join('plugins', item)):
                    try:
                        if config.getboolean('plugins', item) or autoMode:
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
                                self.bitHopper.log_msg("Plugin: " + item + " loaded")
                            except Exception, e:
                                self.bitHopper.log_msg("ERROR LOADING PLUGIN: " + item)
                                self.bitHopper.log_msg(e)
                    except Exception, e:
                        self.bitHopper.log_dbg("Unable to get boolean state for plugin %s: %s") % (item, e)
                        pass

