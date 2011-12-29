#License#
#bitHopper by Colin Rice is licensed under a 
#Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import eventlet, importlib, logging
from eventlet.green import os

class Plugin():
    """Class which loads plugins from folders in the plugins folder."""
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.load_cfg()
        self.load_plugins()
        

    def load_cfg(self):
        """Load all config files from plugin directory"""
        logging.info('Loading Config Files')
        pool_configs = []
        for dirpath, dirnames, filenames in os.walk('plugins'):
            for name in filenames:
                try:
                    if name.split('.')[-1] == 'cfg':
                        pool_configs.append(os.path.join(dirpath, name))
                except Exception, e:
                    logging.info("Unable to load config file for:\n%s \n\n%s") % (dirpath, e)
        self.bitHopper.pool.pool_configs += pool_configs
        self.bitHopper.pool.loadConfig()

    def load_plugins(self):
        """Tries to load all plugins in folder plugins"""
        config = self.bitHopper.config
        try:
            if config.get('pluginmode', 'mode').find('disabled') == -1:
                if config.get('pluginmode', 'mode').find('auto') > -1:
                    autoMode = True
                    logging.info("Plugin loading mode: auto")
                else:
                    autoMode = False
                    logging.info("Plugin loading mode: manual")
            else:
                logging.info("Plugin loading mode: disabled")
                return
        except:
            logging.debug('Unable to find [pluginmode] section from bh.cfg, running with auto plugin loading mode')
            autoMode = True
        logging.info('Loading Plugins')
        possible_plugins = os.listdir('plugins')
        for item in possible_plugins:
            if os.path.isdir(os.path.join('plugins', item)):
                if autoMode:
                    pluginEnabled = True
                else:
                    pluginEnabled = False
                    try:
                        if config.getboolean('plugins', item):
                            pluginEnabled = True
                    except Exception, e:
                        logging.info("" + item + " failed reading main config file: " + str(e))
                        pass
                if pluginEnabled:
                    try:
                        module = importlib.import_module('plugins.' + str(item))
                        bithop_attr = getattr(self.bitHopper, item, None)
                        if bithop_attr is not None:
                            logging.info('name conflict: ' + str(item))
                            continue
                        
                        #Actually call module and store it in bitHopper
                        return_value = module.main(self.bitHopper)
                        if return_value is None:
                            setattr(self.bitHopper, item, module)
                        else:
                            setattr(self.bitHopper, item, return_value)
                        logging.info("" + item + " loaded")
                    except Exception, e:
                        logging.info("ERROR LOADING PLUGIN: " + item)
                        logging.info(e)
                else:
                    logging.info("" + item + " has been disabled")
