#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

try:
    import eventlet
except Exception, e:
    print "You need to install eventlet. See the readme."
    raise e
from eventlet import wsgi
from eventlet.green import os, time
eventlet.monkey_patch()
from eventlet import debug
#debug.hub_blocking_detection(True)

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
from lpbot import LpBot

import sys

class BitHopper():
    def __init__(self, options):
        """Initializes all of the submodules bitHopper uses"""
        self.options = options
        self.lp_callback = lp_callback.LP_Callback(self)
        self.lpBot = None
        self.difficulty = diff.Difficulty(self)           
        self.pool = pool.Pool(self)     
        self.db = database.Database(self)
        self.pool.setup(self) 
        self.speed = speed.Speed(self)
        self.scheduler = scheduler.Scheduler(self)
        self.getwork_store = getwork_store.Getwork_store(self)
        self.data = data.Data(self)       
        self.lp = lp.LongPoll(self)
        self.auth = None
        self.work = work.Work(self)
        self.website = website.bitSite(self)
        eventlet.spawn_n(self.delag_server)

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
        if kwargs and kwargs.get('cat'):
            print time.strftime("[%H:%M:%S] ") + '[' + kwargs.get('cat') + '] ' + str(msg)
        elif self.get_options() == None:
            print time.strftime("[%H:%M:%S] ") +str(msg)
            sys.stdout.flush()
        elif self.get_options().debug == True:
            print time.strftime("[%H:%M:%S] ") +str(msg)
            sys.stdout.flush()
        else: 
            print time.strftime("[%H:%M:%S] ") +str(msg)
            sys.stdout.flush()

    def log_dbg(self, msg, **kwargs):
        if self.get_options().debug == True and kwargs and kwargs.get('cat'):
            self.log_msg('DEBUG: ' + '['+kwargs.get('cat')+"] "+str(msg))
            #sys.stderr.flush()
        elif self.get_options() == None:
            pass
        elif self.get_options().debug == True:
            self.log_msg('DEBUG: ' + str(msg))
            #sys.stderr.flush()
        return

    def log_trace(self, msg, **kwargs):
        if self.get_options().trace == True and kwargs and kwargs.get('cat'):
            self.log_msg('['+kwargs.get('cat')+"] "+msg)
            #sys.stderr.flush()
        elif self.get_options().trace == True:
            self.log_msg(msg)
            #sys.stderr.flush()
        return


    def get_server(self, ):
        return self.pool.get_current()

    def select_best_server(self, ):
        server_name = self.scheduler.select_best_server()
        if not server_name:
            self.log_msg('FATAL Error, scheduler did not return any pool!')
            os._exit(-1)
            
        if self.pool.get_current() != server_name:
            self.pool.set_current(server_name)
            self.log_msg("Server change to " + str(self.pool.get_current()))

        return

    def get_new_server(self, server):
        if server not in self.pool.servers:
            return self.pool.get_current()
        with self.pool.lock:
            self.pool.servers[server]['lag'] = True
        self.log_msg('Lagging. :' + server)
        self.server_update()
        return self.pool.get_current()

    def server_update(self, ):
        if self.scheduler.server_update():
            self.select_best_server()

    def delag_server(self ):
        while True:
            #Delags servers which have been marked as lag.
            #If this function breaks bitHopper dies a long slow death.
            with self.pool.lock:
                self.log_dbg('Running Delager')
                for server in self.pool.get_servers():
                    info = self.pool.servers[server]
                    if info['lag'] == True:
                        data = self.work.jsonrpc_call(server, [])
                        self.log_dbg('Got' + server + ":" + str(data))
                        if data != None:
                            info['lag'] = False
                            self.log_dbg('Delagging')
                        else:
                            self.log_dbg('Not delagging')
            eventlet.sleep(20)

def main():
    parser = optparse.OptionParser(description='bitHopper')
    parser.add_option('--debug', action= 'store_true', default = False, help='Extra error output. Basically print all caught errors')
    parser.add_option('--trace', action= 'store_true', default = False, help='Extra debugging output')
    parser.add_option('--listschedulers', action='store_true', default = False, help='List alternate schedulers available')
    parser.add_option('--port', type = int, default=8337, help='Port to listen on')
    parser.add_option('--scheduler', type=str, default=None, help='Select an alternate scheduler')
    parser.add_option('--threshold', type=float, default=None, help='Override difficulty threshold (default 0.43)')
    parser.add_option('--altslicesize', type=int, default=900, help='Override Default AltSliceScheduler Slice Size of 900')
    parser.add_option('--altminslicesize', type=int, default=60, help='Override Default Minimum Pool Slice Size of 60 (AltSliceScheduler only)')
    parser.add_option('--altslicejitter', type=int, default=0, help='Add some random variance to slice size, disabled by default (AltSliceScheduler only)')
    parser.add_option('--altsliceroundtimebias', action='store_true', default=False, help='Bias slicing slightly by round time duration with respect to round time target (default false)')
    parser.add_option('--altsliceroundtimetarget', type=int, default=1000, help='Round time target based on GHash/s (default 1000 Ghash/s)')
    parser.add_option('--altsliceroundtimemagic', type=int, default=10, help='Round time magic number, increase to bias towards round time over shares')
    parser.add_option('--p2pLP', action='store_true', default=False, help='Starts up an IRC bot to validate LP based hopping.')
    parser.add_option('--ip', type = str, default='', help='IP to listen on')
    parser.add_option('--auth', type = str, default=None, help='User,Password')
    options = parser.parse_args()[0]

    if options.trace == True: options.debug = True

    if options.listschedulers:
        schedulers = ""
        for s in scheduler.Scheduler.__subclasses__():
            schedulers += ", " + s.__name__
        print "Available Schedulers: " + schedulers[2:]
        return

    bithopper_instance = BitHopper(options)

    if options.auth:
        auth = options.auth.split(',')
        bithopper_instance.auth = auth
        if len(auth) != 2:
            print 'User,Password. Not whatever you just entered'
            return
    
    if options.scheduler:
        bithopper_instance.log_msg("Selecting scheduler: " + options.scheduler)
        foundScheduler = False
        for s in scheduler.Scheduler.__subclasses__():
            if s.__name__ == options.scheduler:
                bithopper_instance.scheduler = s(bithopper_instance)
                foundScheduler = True
                break
        if not foundScheduler:            
            bithopper_instance.log_msg("Error couldn't find: " + options.scheduler + ". Using default scheduler.")
            bithopper_instance.scheduler = scheduler.DefaultScheduler(bithopper_instance)
    else:
        bithopper_instance.log_msg("Using default scheduler.")
        bithopper_instance.scheduler = scheduler.DefaultScheduler(bithopper_instance)

    bithopper_instance.select_best_server()

    if options.p2pLP:
        bithopper_instance.log_msg('Starting p2p LP')
        bithopper_instance.lpBot = LpBot(bithopper_instance)

    if not options.debug:
        log = open(os.devnull, 'wb')
    else:
        log = None 
    while True:
        try:
            wsgi.server(eventlet.listen((options.ip,options.port)),bithopper_instance.website.handle_start, log=log)
        except Exception, e:
            print e
    bithopper_instance.db.close()

if __name__ == "__main__":
    main()
