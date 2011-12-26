#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import random, math, logging
import eventlet
from eventlet.green import threading, time, socket

from peak.util import plugins

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class Scheduler(object):
    def __init__(self,bitHopper):
        self.bitHopper = bitHopper
        if self.bitHopper.options.threshold:
            self.difficultyThreshold = self.bitHopper.options.threshold
        else:
            self.difficultyThreshold = 0.435
        self.valid_roles = ['mine', 'mine_lp', 'mine_c', 'mine_charity', 'mine_force', 'mine_lp_force']
        self.valid_roles.extend(['mine_' + coin["short_name"] for coin in self.bitHopper.altercoins.itervalues() if coin["short_name"] != 'btc'])
        hook_announce = plugins.Hook('plugins.lp.announce')
        hook_announce.register(self.mine_lp_force)

        self.loadConfig()
        eventlet.spawn_n(self.bitHopper_server_update)

    def loadConfig(self):
        try:
            self.difficultyThreshold = self.bitHopper.config.getfloat('main', 'threshold')
        except Exception, e:
            logging.debug("Unable to load threshold for selected scheduler from a config file: " + str(e))

    def bitHopper_server_update(self):
        while True:
            self.bitHopper.server_update()
            eventlet.sleep(20)

    def reset(self):
        pass

    def mine_lp_force(self, lp, body, server, block):
        for server_name in self.bitHopper.pool.get_servers():
            server = self.bitHopper.pool.get_entry(server_name)
            if server['role'] == 'mine_lp_force':
                server['role'] = server['default_role']

    def select_charity_server(self):
        server_name = None
        most_shares = self.bitHopper.difficulty['btc'] * 2
        for server in self.bitHopper.pool.get_servers():
            info = self.bitHopper.pool.get_entry(server)
            if info['role'] != 'mine_charity':
                continue
            if info['shares'] > most_shares and info['lag'] == False:
                server_name = server
                most_shares = info['shares']
                logging.debug('select_charity_server: ' + str(server), cat='scheduler-default')

        return server_name

        return server_name   

    def server_to_btc_shares(self,server):
        return self.bitHopper.pool.get_entry(server).btc_shares()

    def server_is_valid(self, server):
        info = self.bitHopper.pool.get_entry(server)
        return info.is_valid() and info['role'] in self.valid_roles

    def select_backup_server(self,):
        reject_rate = 1

        backup_servers = []

        for server in self.bitHopper.pool.get_servers():
            info = self.bitHopper.pool.get_entry(server)
            if info['role'] not in ['backup', 'backup_latehop']:
                continue
            if not info.is_valid():
                continue
            backup_servers.append(info)

        if len(backup_servers) == 0:
            for server in self.bitHopper.pool.get_servers():
                info = self.bitHopper.pool.get_entry(server)
                if info['role'] not in self.valid_roles:
                    continue
                if not info.is_valid():
                    continue
                backup_servers.append(info)

        if len(backup_servers) == 0:
            for server in self.bitHopper.pool.get_servers():
                backup_servers.append(self.bitHopper.pool.get_entry(server))

        backup_servers.sort()

        #for i in backup_servers:
        #    print i['name'] + ":" + str(float(i['rejects']/(i['user_shares']+1)))

        backup_name = []
        for server in backup_servers:
            backup_name.append(server['index_name'])

        return backup_name

    def update_api_server(self,server):
        return

class DefaultScheduler(Scheduler):

    def select_best_server(self,):
        #logging.debug('select_best_server', cat='scheduler-default')
        server_name = None
        difficulty = self.bitHopper.difficulty['btc']
        min_shares = difficulty * self.difficultyThreshold

        #logging.debug('min-shares: ' + str(min_shares), cat='scheduler-default')  
        for server in self.bitHopper.pool.get_servers():
            shares,info = self.server_to_btc_shares(server)
            if not self.server_is_valid(server):
                    continue
            if shares < min_shares:
                min_shares = shares
                #logging.debug('Selecting pool ' + str(server) + ' with shares ' + str(info['shares']), cat='scheduler-default')
                server_name = server
         
        if server_name == None and self.select_charity_server():
            server_name = self.select_charity_server()
        
        if server_name == None:
            return [], self.select_backup_server()

        return [server_name], self.select_backup_server()

        return [server_name], self.select_backup_server()

    def server_update(self,):
        current = self.bitHopper.pool.get_current()
        shares,info = self.server_to_btc_shares(current)
        difficulty = self.bitHopper.difficulty['btc']

        if not self.server_is_valid(current):
            return True

        if shares > (difficulty * self.difficultyThreshold):
            return True

        min_shares = info['shares']

        for server in self.bitHopper.pool.servers:
            pool = self.bitHopper.pool.get_entry(server)
            if pool['shares'] < min_shares:
                min_shares = pool['shares']

        if min_shares < info['shares']*.90:
            return True       

        return False

class WaitPenaltyScheduler(Scheduler):

    def __init__(self, bitHopper):
        Scheduler.__init__(self, bitHopper)
        self.bitHopper = bitHopper
        #self.lastcalled = time.time()
        #self.loadConfig()
        self.reset()
        
    def reset(self,):
        for server in self.bitHopper.pool.get_servers():
            info = self.bitHopper.pool.get_entry(server)
            if 'wait' not in info:
                info['wait'] = 0
            else:
                info['wait'] = float(info['wait'])

    def select_best_server(self,):
        #logging.debug('select_best_server', cat='scheduler-waitpenalty')
        server_name = None
        difficulty = self.bitHopper.difficulty['btc']
        min_shares = difficulty * self.difficultyThreshold

        #logging.debug('min-shares: ' + str(min_shares), cat='scheduler-waitpenalty')  
        for server in self.bitHopper.pool.get_servers():
            shares,info = self.server_to_btc_shares(server)
            shares += float(info['wait']) * difficulty
            if not self.server_is_valid(server):
                continue
            if shares < min_shares:
                min_shares = shares
                #logging.debug('Selecting pool ' + str(server) + ' with shares ' + str(info['shares']), cat='scheduler-waitpenalty')
                server_name = server
         
        if server_name == None and self.select_charity_server:
            server_name = self.select_charity_server()

        if server_name == None:
            return [], self.select_backup_server()

        return [server_name], self.select_backup_server()

    def server_update(self,):
        current = self.bitHopper.pool.get_current()
        shares,info = self.server_to_btc_shares(current)
        difficulty = self.bitHopper.difficulty['btc']

        if not self.server_is_valid(server):
            return True

        if shares > (difficulty * self.difficultyThreshold):
            return True

        for server in self.bitHopper.pool.servers:
            other_shares = self.server_to_btc_shares(server)
            if other_shares < shares:
                return True

        return False

class RoundTimeScheduler(Scheduler):
    def select_best_server(self,):
        return
    def select_backup_server(self,):
        return


class RoundTimeDynamicPenaltyScheduler(Scheduler):
    def select_best_server(self,):
        return
    def select_backup_server(self,):
        return


class SimpleSliceScheduler(Scheduler):
    def __init__(self, bitHopper):
        Scheduler.__init__(self, bitHopper)
        self.bitHopper = bitHopper
        self.sliceinfo = {}
        self.slicesize = 30
        self.lastcalled = time.time()
        self.loadConfig()
        for server in self.bitHopper.pool.servers:
            self.sliceinfo[server] = -1
        self.reset()
    
    def loadConfig(self,):
        Scheduler.loadConfig(self)
        try:
            ss = self.bitHopper.config.getint('defaultscheduler', 'slicesize')
            self.slicesize = ss
        except Exception, e:
            logging.debug("Unable to set slicesize for defaultscheduler from a config file: " + str(e))
            pass

    def reset(self,):
        self.select_best_server()

    def select_best_server(self,):
        #logging.debug('select_best_server', cat='scheduler-default')
        difficulty = self.bitHopper.difficulty['btc']
        min_shares = difficulty * self.difficultyThreshold

        valid_servers = []
        for server in self.bitHopper.pool.get_servers():
            shares,info = self.server_to_btc_shares(server)
            if not self.server_is_valid(server):
                continue
            if shares< min_shares:
                valid_servers.append(server)
         
        for server in valid_servers:
            if server not in self.sliceinfo:
                self.sliceinfo[server] = 0
            if self.sliceinfo[server] == -1:
                self.sliceinfo[server] = 0

        for server in self.sliceinfo:
            if server not in valid_servers:
                self.sliceinfo[server] = -1

        charity_server = self.select_charity_server()
        if valid_servers == [] and charity_server != None: 
            valid_servers.append(charity_server)

        return valid_servers, self.select_backup_server()
   
    def server_update(self,):
        #logging.info(str(self.sliceinfo))
        diff_time = time.time()-self.lastcalled
        self.lastcalled = time.time()
        current = self.sliceinfo[self.bitHopper.pool.get_current()]
        if current == -1:
            return True

        self.sliceinfo[self.bitHopper.pool.get_current()] += diff_time

        if self.bitHopper.pool.servers[self.bitHopper.pool.get_current()]['role'] not in self.valid_roles:
            return True

        valid = []
        for k in self.sliceinfo:
            if self.sliceinfo[k] != -1:
                valid.append(k)

        if len(valid) <=1:
            return True

        for server in valid:
            if current - self.sliceinfo[server] > 30:
                return True

        difficulty = self.bitHopper.difficulty['btc']
        min_shares = difficulty * self.difficultyThreshold

        shares = self.server_to_btc_shares(self.bitHopper.pool.get_current())[0]
        
        if shares > min_shares:
            return True

        return False

class AltSliceScheduler(Scheduler):
    def __init__(self,bitHopper):
        Scheduler.__init__(self,bitHopper)
        self.bitHopper = bitHopper
        self.sliceinfo = {}
        self.name = 'scheduler-altslice'
        self.slicesize = 600
        self.minslicesize = 20
        self.slice_jitter = 0
        self.roundtimebias = False
        self.target_ghash = 1000
        self.parseConfig()
        logging.info('Initializing AltSliceScheduler...', cat=self.name)
        logging.info(' - Min Slice Size: ' + str(self.minslicesize), cat=self.name)
        logging.info(' - Slice Size: ' + str(self.slicesize), cat=self.name)
        logging.info(' - Jitter: ' + str(self.slice_jitter), cat=self.name)
        self.lastcalled = time.time()
        self.target_duration = 0
        self.sbs_count = 0
        self.initDone = False
        self.reset()

    #noinspection PyBroadException
    def parseConfig(self):
        try:
            self.slicesize = self.bitHopper.config.getint('AltSliceScheduler', 'slicesize')
        except: pass

        try:
            self.minslicesize = self.bitHopper.config.getint('AltSliceScheduler', 'min_slicesize')
        except: pass

        try:
            self.slice_jitter = self.bitHopper.config.getint('AltSliceScheduler', 'slice_jitter')
        except: pass

        try:
            self.roundtimebias = self.bitHopper.config.getboolean('AltSliceScheduler', 'roundtimebias')
        except: pass

        try:
            self.roundtimetarget = self.bitHopper.config.getint('AltSliceScheduler', 'roundtimetarget')
        except: pass

        try:
            self.roundtimemagic = self.bitHopper.config.getint('AltSliceScheduler', 'roundtimemagic')
        except: pass

    def reset(self,):
        for server in self.bitHopper.pool.get_servers():
            info = self.bitHopper.pool.get_entry(server)
            info['slice'] = -1
            info['slicedShares'] = 0
            if 'init' not in info:
                info['init'] = False
        if self.roundtimebias:
            difficulty = self.bitHopper.difficulty['btc']
            one_ghash = 1000000 * 1000
            target_ghash = one_ghash * int(self.target_ghash) * (1+self.difficultyThreshold)
            logging.info(' - Target Round Time Bias GHash/s (derived): ' + str(float(target_ghash/one_ghash)), cat=self.name)
            self.target_duration = difficulty * (2**32) / target_ghash
            logging.info(" - Target duration: " + str(int(self.target_duration)) + "(s) or " + str(int(self.target_duration/60)) + " minutes", cat=self.name)
            
    def select_best_server(self,):
        logging.log(0, 'select_best_server', cat=self.name)
        server_name = None
        difficulty = self.bitHopper.difficulty['btc']
        min_shares = difficulty * self.difficultyThreshold

        current_server = self.bitHopper.pool.get_current()
        reslice = True
        fullinit = True
        allSlicesDone = True
      
        for server in self.bitHopper.pool.get_servers():
            info = self.bitHopper.pool.get_entry(server)
            if info['slice'] > 0:
                reslice = False
                allSlicesDone = False
            if 'init' in info and info['init'] == False and info['role'] in self.valid_roles:
                logging.log(0, server + " not yet initialized", cat=self.name)
                fullinit = False
            if 'init' not in info:
                fullinit = False
            shares = info['shares']
            if 'penalty' in info:
                shares = shares * float(info['penalty'])
            # favor slush over other pools if low enough
            if info['role'] in ['mine_c'] and shares * 4 < min_shares:
                fullinit = True
      
        if self.bitHopper.pool.get_current() is None or allSlicesDone == True:
            reslice = True
        elif self.bitHopper.pool.get_entry(current_server)['lag']:
            reslice = True

        if (fullinit and self.initDone == False) or self.sbs_count > 64: # catch long init
            self.initDone = True
            reslice = True
         
        #logging.debug('allSlicesDone: ' + str(allSlicesDone) + ' fullinit: ' + str(fullinit) + ' initDone: ' + str(self.initDone), cat='reslice')
        if reslice == True:
            logging.info('Re-Slicing...', cat=self.name)
            totalshares = 1
            totalweight = 0
            server_shares = {}
            for server in self.bitHopper.pool.get_servers():
                shares,info = self.server_to_btc_shares(server)
                shares += 1
                if not self.server_is_valid(server):
                    continue
                if shares < min_shares and shares >= 0:               
                    totalshares = totalshares + shares
                    info['slicedShares'] = shares
                    server_shares[server] = shares
                else:
                    logging.log(0, server + ' skipped ' + str(shares))
                    continue
            # find total weight
            for server in self.bitHopper.pool.get_servers():
                info = self.bitHopper.pool.get_entry(server)
                if not self.server_is_valid(server):
                    continue
                if server not in server_shares:
                    continue
                if server_shares[server] < min_shares and server_shares[server] > 0:
                    totalweight += 1/(float(server_shares[server])/totalshares)
                      
                      
            # round time biasing
            tb_delta = {}
            tb_log_delta = {}
            pos_weight = {}
            neg_weight = {}
            adj_slice = {}
            # TODO punish duration estimates weighed by temporal duration
            if self.roundtimebias:
                # delta from target
                for server in self.bitHopper.pool.get_servers():              
                    info = self.bitHopper.pool.get_entry(server)
                    if info['role'] not in self.valid_roles:
                        continue
                    if info['duration'] <= 0:
                        continue
                    if server not in server_shares:
                        continue
                    tb_delta[server] = self.target_duration - info['duration'] + 1
                    tb_log_delta[server] = math.log(abs(tb_delta[server]))
                    logging.log(0, '  ' + server + " delta: " + str(tb_delta[server]) + " log_delta: " + str(tb_log_delta[server]), cat=self.name)            

                # pos/neg_total
                pos_total = 0
                neg_total = 0
                for server in self.bitHopper.pool.get_servers():              
                    info = self.bitHopper.pool.get_entry(server)
                    if info['role'] not in self.valid_roles:
                        continue
                    if info['duration'] <= 0:
                        continue
                    if server not in server_shares:
                        continue
                    if tb_delta[server] >= 0: pos_total += tb_log_delta[server]
                    if tb_delta[server]  < 0: neg_total += tb_log_delta[server]
                logging.log(0, "pos_total: " + str(pos_total) + " / neg_total: " + str(neg_total), cat=self.name)   
                
                # preslice            
                for server in self.bitHopper.pool.get_servers():
                    if server in tb_delta:
                        info = self.bitHopper.pool.get_entry(server)
                        if info['isDurationEstimated'] == True and info['duration_temporal'] < 300:
                            tb_delta[server] = 0
                        else:
                            if tb_delta[server] >= 0:
                                pos_weight[server] = tb_log_delta[server] / pos_total
                                logging.log(0, server + " pos_weight: " + str(pos_weight[server]), cat=self.name)
                            elif tb_delta[server] < 0:
                                neg_weight[server] = tb_log_delta[server] / neg_total
                                logging.log(0, server + " neg_weight: " + str(neg_weight[server]), cat=self.name)
                                                    

            # allocate slices         
            for server in self.bitHopper.pool.get_servers():
                info = self.bitHopper.pool.get_entry(server)
                if info['role'] not in self.valid_roles:
                    continue
                if server not in server_shares:
                    continue
                shares = server_shares[server] + 1
                if shares <= 0:
                    continue                    
                if shares < min_shares and shares > 0:
                    weight = 0
                    logging.log(0, 'tb_delta: ' + str(len(tb_delta)) + ' / server_shares: ' + str(len(server_shares)), cat=self.name)
                    if self.roundtimebias:
                        if len(tb_delta) == 1 and len(server_shares) == 1:
                            # only 1 server to slice (zzz)
                            if info['duration'] > 0:
                                slice = self.slicesize
                            else:
                                slice = 0
                        else:
                            weight = 1/(float(shares)/totalshares)
                            slice = weight * self.slicesize / totalweight
                            if self.slice_jitter != 0:
                                jitter = random.randint(0-self.slice_jitter, self.slice_jitter)
                                slice += jitter
                    else:                  
                        if shares == totalshares:
                            # only 1 server to slice (zzz)
                            slice = self.slicesize
                        else:
                            weight = 1/(float(shares)/totalshares)
                            slice = weight * self.slicesize / totalweight
                            if self.slice_jitter != 0:
                                jitter = random.randint(0-self.slice_jitter, self.slice_jitter)
                                slice += jitter
                    info['slice'] = slice
                    if self.bitHopper.options.debug:
                        logging.debug(server + " sliced to " + "{0:.2f}".format(info['slice']) + '/' + "{0:d}".format(int(self.slicesize)) + '/' + str(shares) + '/' + "{0:.3f}".format(weight) + '/' + "{0:.3f}".format(totalweight) , cat=self.name)
                    else:
                        logging.info(server + " sliced to " + "{0:.2f}".format(info['slice']), cat=self.name)
                   
            # adjust based on round time bias
            if self.roundtimebias:
                logging.debug('Check if apply Round Time Bias: tb_log_delta: ' + str(len(tb_log_delta)) + ' == servers: ' + str(len(server_shares)), cat=self.name)
            if self.roundtimebias and len(tb_log_delta) >= 1:
                logging.info('>>> Apply Round Time Bias === ', cat=self.name)
                ns_total = 0
                adj_factor = self.roundtimemagic
                logging.log(0, '     server: ' + str(server), cat=self.name)
                for server in self.bitHopper.pool.get_servers():
                    info = self.bitHopper.pool.get_entry(server)
                    if server not in tb_log_delta: continue # no servers to adjust
                    logging.log(0, '     server(tld): ' + server, cat=self.name)
                    if server in pos_weight:
                        adj_slice[server] = info['slice'] + adj_factor * pos_weight[server]
                        logging.log(0, '     server (pos): ' + str(adj_slice[server]), cat=self.name)
                        ns_total += adj_slice[server]            
                    elif server in neg_weight:                  
                        adj_slice[server] = info['slice'] - adj_factor * neg_weight[server]
                        logging.log(0, '     server (neg): ' + str(adj_slice[server]), cat=self.name)
                        ns_total += adj_slice[server]
                # re-slice the slices
                ad_totalslice = 0
                for server in self.bitHopper.pool.get_servers():
                    info = self.bitHopper.pool.get_entry(server)
                    if info['role'] not in self.valid_roles:
                        continue
                    if info['shares'] < 0: continue
                    if server not in server_shares: continue
                    shares = server_shares[server] + 1
                    if shares < min_shares and shares > 0:
                        if server in adj_slice:
                            ad_totalslice += adj_slice[server]
                        else:
                            ad_totalslice += info['slice']
                         
                for server in self.bitHopper.pool.get_servers():            
                    info = self.bitHopper.pool.get_entry(server)
                    if info['role'] not in self.valid_roles:
                        continue
                    if info['shares'] < 0: continue
                    if server not in server_shares: continue
                    if server not in tb_log_delta: continue # no servers to adjust
                    shares = server_shares[server] + 1
                    if shares < min_shares and shares > 0:
                        if server in adj_slice:
                            previous = info['slice']
                            info['slice'] = self.slicesize * (adj_slice[server] / ad_totalslice)
                            if self.bitHopper.options.debug:
                                logging.debug(server + " _adjusted_ slice to " + "{0:.2f}".format(info['slice']) + '/' + "{0:d}".format(int(self.slicesize)) + '/' + str(shares) + '/' + "{0:.3f}".format(adj_slice[server]) + '/' + "{0:.3f}".format(ad_totalslice) , cat=self.name)
                            else:
                                logging.info('  > ' + server + " _adjusted_ slice to " + "{0:.2f}".format(info['slice']) + " from {0:.2f}".format(previous), cat=self.name)
                        else:
                            info['slice'] = self.slicesize * (info['slice'] / ad_totalslice)
                            if self.bitHopper.options.debug:
                                logging.debug(server + " sliced to " + "{0:.2f}".format(info['slice']) + '/' + "{0:d}".format(int(self.slicesize)) + '/' + str(shares) + '/na/' + "{0:.3f}".format(ad_totalslice) , cat=self.name)
                            else:
                                logging.info(server + " sliced to " + "{0:.2f}".format(info['slice']), cat=self.name)
                                     
            # min share adjustment
            for server in self.bitHopper.pool.get_servers():
                info = self.bitHopper.pool.get_entry(server)
                if info['role'] not in self.valid_roles:
                    continue
                if info['shares'] < 0: continue
                if server not in server_shares: continue
                if info['slice'] < self.minslicesize:
                    info['slice'] = self.minslicesize
                    if self.bitHopper.options.debug:
                        logging.debug(server + " (min)sliced to " + "{0:.2f}".format(info['slice']) + '/' + "{0:d}".format(int(self.slicesize)) + '/' + str(shares) + '/' + "{0:d}".format(info['duration']), cat=self.name)
                    else:
                        logging.info(server + " (min)sliced to " + "{0:.2f}".format(info['slice']), cat=self.name)                                           
   
        # Pick server with largest slice first
        max_slice = -1
        for server in self.bitHopper.pool.get_servers():
            info = self.bitHopper.pool.get_entry(server)
            shares = info['shares']
            if 'penalty' in info:
                shares = shares * float(info['penalty'])
            # favor slush over other pools if low enough
            if info['role'] in ['mine_c'] and shares * 4 < min_shares:
                max_slice = info['slice']
                server_name = server
                continue
            if  info['slice'] > 0 and self.server_is_valid(server):
                if max_slice == -1:
                    max_slice = info['slice']
                    server_name = server
                if info['slice'] > max_slice:
                    max_slice = info['slice']
                    server_name = server
       
        if server_name is None: server_name = self.select_charity_server()
                   
        #logging.debug('server_name: ' + str(server_name), cat=self.name)
        if server_name is None:
            server_list = []
        else:
            server_list = [server_name]
        return server_list, self.select_backup_server()
         

    def server_update(self,):
        #logging.debug('server_update', cat='server_update')
        diff_time = time.time()-self.lastcalled
        self.lastcalled = time.time()
        current = self.bitHopper.pool.get_current()
        shares,info = self.server_to_btc_shares(current)
        info['slice'] = info['slice'] - diff_time
        #logging.debug(current_server + ' slice ' + str(info['slice']), cat='server_update' )
        if not self.initDone:
            self.bitHopper.select_best_server()
            return True
        if info['slice'] <= 0: return True
          
        # shares are now less than shares at time of slicing (new block found?)
        if info['slicedShares'] > info['shares']:
            logging.debug("slicedShares > shares")
            return True
          
        # double check role
        if info['role'] not in self.valid_roles: 
            return True
          
        # check to see if threshold exceeded
        difficulty = self.bitHopper.difficulty['btc']
        min_shares = difficulty * self.difficultyThreshold
    
        if shares > min_shares:
            logging.debug("shares > min_shares")
            info['slice'] = -1 # force switch
            return True
          
        return False

    def update_api_server(self,server):
        info = self.bitHopper.pool.get_entry(server)
        if info['role'] in ['info', 'disable'] and info['slice'] > 0:
            info['slice'] = -1
        return

