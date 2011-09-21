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
eventlet.monkey_patch()
#from eventlet import debug
#debug.hub_blocking_detection(True)

from peak.util import plugins

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


import ConfigParser
import sys

class BitHopper():
    def __init__(self, options, config):
        """Initializes all of the submodules bitHopper uses"""
        self.options = options
        self.config = config
        self.lp_callback = lp_callback.LP_Callback(self)
        self.difficulty = diff.Difficulty(self)           
        self.pool = pool.Pool(self)
        self.db = database.Database(self)
        self.api = api.API(self)
        self.pool.setup(self)
        self.work = work.Work(self)
        self.speed = speed.Speed(self)
        self.scheduler = None
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
        self.data.reject_callback(server, data, user, password)

    def data_callback(self, server, data, user, password):
        self.data.data_callback(server, data, user, password)

    def update_payout(self, server, payout):
        self.db.set_payout(server, float(payout))
        self.pool.servers[server]['payout'] = float(payout)

    def get_options(self):
        return self.options

    def log_msg(self, msg, **kwargs):
        if kwargs and kwargs.get("cat"):
            print time.strftime("[%H:%M:%S] ") + "[" + kwargs.get("cat") + "] " + str(msg)
        elif self.get_options() == None:
            print time.strftime("[%H:%M:%S] ") + str(msg)
            sys.stdout.flush()
        elif self.get_options().debug == True:
            print time.strftime("[%H:%M:%S] ") + str(msg)
            sys.stdout.flush()
        else: 
            print time.strftime("[%H:%M:%S] ") + str(msg)
            sys.stdout.flush()

    def log_dbg(self, msg, **kwargs):
        if self.get_options().debug == True and kwargs and kwargs.get("cat"):
            self.log_msg("DEBUG: " + "[" + kwargs.get("cat") + "] " + str(msg))
            #sys.stderr.flush()
        elif self.get_options() == None:
            pass
        elif self.get_options().debug == True:
            self.log_msg("DEBUG: " + str(msg))
            #sys.stderr.flush()
        return

    def log_trace(self, msg, **kwargs):
        if self.get_options().trace == True and kwargs and kwargs.get("cat"):
            self.log_msg("TRACE: " + "[" + kwargs.get("cat") + "] " + str(msg))
            #sys.stderr.flush()
        elif self.get_options().trace == True:
            self.log_msg("TRACE: " + str(msg))
            #sys.stderr.flush()
        return


    def get_server(self, ):
        return self.pool.get_current()

    def select_best_server(self, ):
        server_name = self.scheduler.select_best_server()
        if not server_name:
            self.log_msg('FATAL Error, scheduler did not return any pool!')
            os._exit(-1)

        old_server = self.pool.get_current()
            
        if self.pool.get_current() != server_name:
            self.pool.set_current(server_name)
            self.log_msg("Server change to " + str(self.pool.get_current()))
            servers = self.pool.servers
            if servers[server_name]['coin'] != servers[old_server]['coin']:
                self.log_msg("Change in coin type. Triggering LP")
                work, server_headers, server  = self.work.jsonrpc_getwork(server_name, [], {}, "", "")
                self.bitHopper.lp_callback.new_block(work, server_name)

        return

    def get_new_server(self, server):
        if server not in self.pool.servers:
            return self.pool.get_current()
        self.pool.servers[server]['lag'] = True
        self.log_msg('Lagging. :' + server)
        self.select_best_server()
        return self.pool.get_current()

    def server_update(self, ):
        if self.scheduler.server_update():
            self.select_best_server()

    def delag_server(self ):
        while True:
            #Delags servers which have been marked as lag.
            #If this function breaks bitHopper dies a long slow death.
            self.log_dbg('Running Delager')
            for server in self.pool.get_servers():
                info = self.pool.servers[server]
                if info['lag'] == True:
                    data, headers = self.work.jsonrpc_call(server, [])
                    self.log_dbg('Got' + server + ":" + str(data))
                    if data != None:
                        info['lag'] = False
                        self.log_dbg('Delagging')
                    else:
                        self.log_dbg('Not delagging')
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
    parser.add_option('--altslicesize', type=int, default=900, help='Override Default AltSliceScheduler Slice Size of 900')
    parser.add_option('--altminslicesize', type=int, default=60, help='Override Default Minimum Pool Slice Size of 60 (AltSliceScheduler only)')
    parser.add_option('--altslicejitter', type=int, default=0, help='Add some random variance to slice size, disabled by default (AltSliceScheduler only)')
    parser.add_option('--altsliceroundtimebias', action='store_true', default=False, help='Bias slicing slightly by round time duration with respect to round time target (default false)')
    parser.add_option('--altsliceroundtimetarget', type=int, default=1000, help='Round time target based on GHash/s (default 1000 Ghash/s)')
    parser.add_option('--altsliceroundtimemagic', type=int, default=10, help='Round time magic number, increase to bias towards round time over shares')
    parser.add_option('--config', type=str, default='bh.cfg', help='Select an alternate main config file from bh.cfg')
    parser.add_option('--p2pLP', action='store_true', default=False, help='Starts up an IRC bot to validate LP based hopping.')
    parser.add_option('--ip', type = str, default='', help='IP to listen on')
    parser.add_option('--auth', type = str, default=None, help='User,Password')
    parser.add_option('--logconnections', default = False, action='store_true', help='show connection log')
#    parser.add_option('--simple_logging', default = False, action='store_true', help='remove RCP logging from output')
    options = parser.parse_args()[0]

    if options.trace == True: options.debug = True

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
            os._exit(-1)        
        config.read(os.path.join(application_path, options.config))
    except:
        if not os.path.exists(options.config):
            print "Missing " + options.config + " may need to rename bh.cfg.default"
            os._exit(-1)        
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
        bithopper_instance.log_msg("Selecting scheduler: " + scheduler_name)
        foundScheduler = False
        for s in scheduler.Scheduler.__subclasses__():
            if s.__name__ == scheduler_name:
                bithopper_instance.scheduler = s(bithopper_instance)
                foundScheduler = True
                break
        if not foundScheduler:            
            bithopper_instance.log_msg("Error couldn't find: " + scheduler_name + ". Using default scheduler.")
            bithopper_instance.scheduler = scheduler.DefaultScheduler(bithopper_instance)
    else:
        bithopper_instance.log_msg("Using default scheduler.")
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
                bithopper_instance.log_dbg("Unable to load main listening port from config file")
                pass
            socket.setdefaulttimeout(None)
            wsgi.server(eventlet.listen((options.ip,listen_port)),bithopper_instance.website.handle_start, log=log)
            socket.setdefaulttimeout(lastDefaultTimeout)
            break
        except Exception, e:
            bithopper_instance.log_msg("Exception in wsgi server loop, restarting wsgi in 60 seconds\n%s" % (str(e)))
            eventlet.sleep(60)
    bithopper_instance.db.close()

if __name__ == "__main__":
    main()
