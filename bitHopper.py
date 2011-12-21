#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import warnings
warnings.filterwarnings('ignore','' , UserWarning)

try:
    import eventlet
except Exception, e:
    print "You need to install greenlet. See the readme."
    raise e
from eventlet import wsgi, greenpool
from eventlet.green import os, time, socket

#Not patching thread so we can spin of db file ops.
eventlet.monkey_patch(os=True, select=True, socket=True, thread=False, time=True, psycopg=True)
#from eventlet import debug
#debug.hub_blocking_detection(True)

from peak.util import plugins

import logging

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

import optparse

import work
import diff
import pool
import speed
import database
import scheduler
import website
import getwork_store
import data
import lp
import lp_callback
import plugin
import api
import exchange


import ConfigParser
import sys



class BitHopper():
    def __init__(self, options, config):
        """Initializes all of the submodules bitHopper uses"""
        
        #Logging
        
        logging.basicConfig(stream=sys.stdout, format="%(asctime)s %(module)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level = logging.INFO)
        
        self.options = options
        self.config = config        
        altercoins = ConfigParser.ConfigParser()
        altercoins.read(os.path.join(sys.path[0], "whatevercoin.cfg"))
        self.altercoins = {}
        for coin in altercoins.sections():
            self.altercoins[coin] = dict(altercoins.items(coin))
            self.altercoins[coin]['recent_difficulty'] = float(self.altercoins[coin]['recent_difficulty'])
        self.scheduler = None
        self.lp_callback = lp_callback.LP_Callback(self)
        self.difficulty = diff.Difficulty(self)  
        self.exchange = exchange.Exchange(self)
        self.pool = None        
        self.db = database.Database(self)                       
        self.pool = pool.Pool_Parse(self)
        self.api = api.API(self) 
        self.pool.setup(self)
        self.work = work.Work(self)
        self.speed = speed.Speed()
        self.getwork_store = getwork_store.Getwork_store(self)
        self.data = data.Data(self)       
        self.lp = lp.LongPoll(self)
        self.auth = None
        
        self.website = website.bitSite(self)
        self.pile = greenpool.GreenPool()
        self.plugin = plugin.Plugin(self)
        self.pile.spawn_n(self.delag_server)

    def reloadConfig(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.options.config)
        with self.pool.lock:
            self.pool.loadConfig()
        
    def reject_callback(self, server, data, user, password):
        eventlet.spawn_n(self.data.reject_callback, server, data, user, password)

    def data_callback(self, server, data, user, password):
        eventlet.spawn_n(self.data.data_callback, server, data, user, password)

    def update_payout(self, server, payout):
        eventlet.spawn_n(self.db.set_payout, server, float(payout))
        self.pool.servers[server]['payout'] = float(payout)

    def get_options(self):
        return self.options

    def get_server(self, ):
        return self.pool.get_current()

    def select_best_server(self, ):
        if self.scheduler == None:
            server_list = [self.pool.servers.keys()[0]]
            backup_list = []
        else:
            server_list, backup_list = self.scheduler.select_best_server()

        old_server = self.pool.get_current()
            
        #Find the server with highest priority
        max_priority = 0;
        for server in server_list:
            info = self.pool.get_entry(server)
            if info['priority'] > max_priority:
                max_priority = info['priority']

        #Return all servers with this priority
        server_list = [server for server in server_list 
                       if lambda x:self.pool.get_entry(x)['priority'] >= max_priority]

        if len(server_list) == 0:
            try:
                backup_type = self.config.get('main', 'backup_type')
            except:
                backup_type = 'rejectrate'

            if backup_type == 'slice':
                server_list = backup_list

            elif backup_type == 'rejectrate':
                server_list = [backup_list[0]]

            elif backup_type == 'earlyhop':
                backup_list.sort(key=lambda pool:self.pool.servers[pool]['shares'])
                server_list = [backup_list[0]]

            elif backup_type == 'latehop':
                backup_list.sort(key=lambda pool: -1*self.pool.servers[pool]['shares'])
                server_list = [backup_list[0]]

        if len(server_list) == 0:
            logging.info('FATAL Error, scheduler did not return any pool!')
            os._exit(1)

        self.pool.current_list = server_list
        self.pool.build_server_map()
        return

    def get_new_server(self, server):
        if server not in self.pool.servers:
            return self.pool.get_current()
        self.pool.servers[server]['lag'] = True
        logging.info('Lagging. :' + server)
        self.select_best_server()
        return self.pool.get_current()

    def server_update(self, ):
        if self.scheduler.server_update():
            self.select_best_server()

    def delag_server(self ):
        while True:
            #Delags servers which have been marked as lag.
            #If this function breaks bitHopper dies a long slow death.
            logging.debug('Running Delager')
            for server in self.pool.get_servers():
                info = self.pool.servers[server]
                if info['lag'] == True:
                    data, headers = self.work.jsonrpc_call(server, [])
                    logging.debug('Got' + server + ":" + str(data))
                    if data != None:
                        info['lag'] = False
                        logging.debug('Delagging')
                    else:
                        logging.debug('Not delagging')
            sleeptime = self.config.getint('main', 'delag_sleep')
            eventlet.sleep(sleeptime)

def main():
    parser = optparse.OptionParser(description='bitHopper')
    parser.add_option('--debug', action= 'store_true', default = False, help='Extra error output. Basically print all caught errors')
    parser.add_option('--trace', action= 'store_true', default = False, help='Extra debugging output')
    parser.add_option('--listschedulers', action='store_true', default = False, help='List alternate schedulers available')
    parser.add_option('--port', type = int, default=8337, help='Port to listen on')
    parser.add_option('--scheduler', type=str, default='DefaultScheduler', help='Select an alternate scheduler')
    parser.add_option('--threshold', type=float, default=None, help='Override difficulty threshold (default 0.43)')
    parser.add_option('--config', type=str, default='bh.cfg', help='Select an alternate main config file from bh.cfg')
    parser.add_option('--ip', type = str, default='', help='IP to listen on')
    parser.add_option('--auth', type = str, default=None, help='User,Password')
    parser.add_option('--logconnections', default = False, action='store_true', help='show connection log')
#    parser.add_option('--simple_logging', default = False, action='store_true', help='remove RCP logging from output')
    options = parser.parse_args()[0]

    if options.trace or options.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)    
    

    if options.listschedulers:
        schedulers = ""
        for s in scheduler.Scheduler.__subclasses__():
            schedulers += ", " + s.__name__
        print "Available Schedulers: " + schedulers[2:]
        return
    
    config = ConfigParser.ConfigParser()
    try:
        # determine if application is a script file or frozen exe
        if hasattr(sys, 'frozen'):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)
        if not os.path.exists(os.path.join(application_path, options.config)):
            print "Missing " + options.config + " may need to rename bh.cfg.default"
            os._exit(1)
        config.read(os.path.join(application_path, options.config))
    except:
        if not os.path.exists(options.config):
            print "Missing " + options.config + " may need to rename bh.cfg.default"
            os._exit(1)
        config.read(options.config)
    
    bithopper_instance = BitHopper(options, config)

    if options.auth:
        auth = options.auth.split(',')
        bithopper_instance.auth = auth
        if len(auth) != 2:
            print 'User,Password. Not whatever you just entered'
            return
    
    # auth from config
    try:
        c = config.get('auth', 'username'), config.get('auth', 'password')
        bithopper_instance.auth = c
    except:
        pass
    
    override_scheduler = False
    
    if options.scheduler != None:
        scheduler_name = options.scheduler
        override_scheduler = True
    try:
        sched = config.get('main', 'scheduler')
        if sched != None:
            override_scheduler = True
            scheduler_name = sched
    except:
        pass
    
    if override_scheduler:
        logging.info("Selecting scheduler: " + scheduler_name)
        foundScheduler = False
        for s in scheduler.Scheduler.__subclasses__():
            if s.__name__ == scheduler_name:
                bithopper_instance.scheduler = s(bithopper_instance)
                foundScheduler = True
                break
        if not foundScheduler:            
            logging.info("Error couldn't find: " + scheduler_name + ". Using default scheduler.")
            bithopper_instance.scheduler = scheduler.DefaultScheduler(bithopper_instance)
    else:
        logging.info("Using default scheduler.")
        bithopper_instance.scheduler = scheduler.DefaultScheduler(bithopper_instance)

    bithopper_instance.select_best_server()

    lastDefaultTimeout = socket.getdefaulttimeout()  

    if options.logconnections:
        log = None
    else:
        log = open(os.devnull, 'wb')

    hook = plugins.Hook('plugins.bithopper.startup')
    hook.notify(bithopper_instance, config, options)
        
    while True:
        try:
            listen_port = options.port            
            try:
                listen_port = config.getint('main', 'port')
            except ConfigParser.Error:
                logging.debug("Unable to load main listening port from config file")
                pass

            #This ugly wrapper is required so wsgi server doesn't die
            socket.setdefaulttimeout(None)
            wsgi.server(eventlet.listen((options.ip,listen_port), backlog=500),bithopper_instance.website.handle_start, log=log, max_size = 8000)
            socket.setdefaulttimeout(lastDefaultTimeout)
            break
        except Exception, e:
            logging.info("Exception in wsgi server loop, restarting wsgi in 60 seconds\n%s" % (str(e)))
            eventlet.sleep(60)
    bithopper_instance.db.close()

if __name__ == "__main__":
    main()
