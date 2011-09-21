#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import random
import math
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
        self.valid_roles = ['mine', 'mine_nmc', 'mine_lp', 'mine_c', 'mine_ixc', 'mine_i0c', 'mine_scc', 'mine_charity', 'mine_force', 'mine_lp_force']
        hook_announce = plugins.Hook('plugins.lp.announce')
        hook_announce.register(self.mine_lp_force)

        self.loadConfig()
        eventlet.spawn_n(self.bitHopper_server_update)

    def loadConfig(self):
        try:
            self.difficultyThreshold = self.bitHopper.config.getfloat('main', 'threshold')
        except Exception, e:
            self.bitHopper.log_dbg("Unable to load threshold for selected scheduler from a config file: " + str(e))
            pass

    def bitHopper_server_update(self):
        while True:
            self.bitHopper.server_update()
            eventlet.sleep(20)

    def reset(self):
        pass

    def mine_lp_force(self, lp, body, server, block):
        for server_name, server in self.bitHopper.pool.get_servers().items():
            if server['role'] == 'mine_lp_force':
                server['role'] = server['default_role']

    def select_charity_server(self):
        server_name = None
        most_shares = self.bitHopper.difficulty.get_difficulty() * 2
        for server in self.bitHopper.pool.get_servers():
            info = self.bitHopper.pool.get_entry(server)
            if info['role'] != 'mine_charity':
                continue
            if info['shares'] > most_shares and info['lag'] == False:
                server_name = server
                most_shares = info['shares']
                self.bitHopper.log_dbg('select_charity_server: ' + str(server), cat='scheduler-default')

        return server_name

    def select_latehop_server(self):
        server_name = None
        max_share_count = 1
        for server in self.bitHopper.pool.get_servers():
            info = self.bitHopper.pool.get_entry(server)
            if info['api_lag'] or info['lag']:
                continue
            if info['role'] != 'backup_latehop':
                continue
            if info['shares'] > max_share_count:
                server_name = server
                max_share_count = info['shares']
                #self.bitHopper.log_dbg('select_latehop_server: ' + str(server), cat='scheduler-default')

        return server_name   

    def server_to_btc_shares(self,server):
        difficulty = self.bitHopper.difficulty.get_difficulty()
        nmc_difficulty = self.bitHopper.difficulty.get_nmc_difficulty()
        ixc_difficulty = self.bitHopper.difficulty.get_ixc_difficulty()
        i0c_difficulty = self.bitHopper.difficulty.get_i0c_difficulty()
        scc_difficulty = self.bitHopper.difficulty.get_scc_difficulty()
        info = self.bitHopper.pool.get_entry(server)
        if info['coin'] in ['btc']:
            shares = info['shares']
        elif info['coin'] in ['nmc']:
            shares = info['shares']*difficulty / nmc_difficulty
        elif info['coin'] in ['ixc']:
            shares = info['shares']*difficulty / ixc_difficulty
        elif info['coin'] in ['i0c']:
            shares = info['shares']*difficulty / i0c_difficulty
        elif info['coin'] in ['scc']:
            shares = info['shares']*difficulty / scc_difficulty
        else:
            shares = difficulty

        if info['role'] == 'mine_c':
            #Checks if shares are to high and if so sends it through the roof
            #So we don't mine it.
            c = int(info['c'])
            hashrate = float(info['ghash'])
            hopoff = difficulty * (self.difficultyThreshold - 503131/(1173666 + c*hashrate))
            if shares > hopoff:
                shares = 2*difficulty

        if info['role'] in ['mine_force', 'mine_lp_force']:
            shares = 0
        # apply penalty
        if 'penalty' in info:
            shares = shares * float(info['penalty'])
        return shares, info

    def select_backup_server(self,):
        server_name = self.select_latehop_server()
        reject_rate = 1      

        if server_name == None:
            for server in self.bitHopper.pool.get_servers():
                info = self.bitHopper.pool.get_entry(server)
                if info['role'] not in ['backup', 'backup_latehop']:
                    continue
                if info['lag']:
                    continue
                shares = info['user_shares'] + 1
                rr_server = float(info['rejects'])/shares
                if 'penalty' in info:
                    rr_server += float(info['penalty'])/100
                if rr_server < reject_rate:
                    server_name = server
                    reject_rate = rr_server

        if server_name == None:
            #self.bitHopper.log_dbg('Try another backup' + str(server), cat='scheduler-default')
            min_shares = 10**10
            for server in self.bitHopper.pool.get_servers():
                shares,info = self.server_to_btc_shares(server)
                if info['role'] not in self.valid_roles:
                    continue
                if shares < min_shares and not info['lag']:
                    min_shares = shares
                    server_name = server
          
        if server_name == None:
            #self.bitHopper.log_dbg('Try another backup pt2' + str(server), cat='scheduler-default')
            for server in self.bitHopper.pool.get_servers():
                info = self.bitHopper.pool.get_entry(server)
                if info['role'] != 'backup':
                    continue
                server_name = server
                break

        return server_name

    def update_api_server(self,server):
        return

class DefaultScheduler(Scheduler):

    def select_best_server(self,):
        #self.bitHopper.log_dbg('select_best_server', cat='scheduler-default')
        server_name = None
        difficulty = self.bitHopper.difficulty.get_difficulty()
        min_shares = difficulty * self.difficultyThreshold

        #self.bitHopper.log_dbg('min-shares: ' + str(min_shares), cat='scheduler-default')  
        for server in self.bitHopper.pool.get_servers():
            shares,info = self.server_to_btc_shares(server)
            if info['api_lag'] or info['lag']:
                continue
            if info['role'] not in self.valid_roles:
                continue
            if shares < min_shares:
                min_shares = shares
                #self.bitHopper.log_dbg('Selecting pool ' + str(server) + ' with shares ' + str(info['shares']), cat='scheduler-default')
                server_name = server
         
        if server_name == None:
            server_name = self.select_charity_server()

        if server_name == None:     
            server_name = self.select_backup_server()

        return server_name

    def server_update(self,):
        current = self.bitHopper.pool.get_current()
        shares,info = self.server_to_btc_shares(current)
        difficulty = self.bitHopper.difficulty.get_difficulty()

        if info['role'] not in self.valid_roles:
            return True
    
        if info['api_lag'] or info['lag']:
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
        #self.bitHopper.log_dbg('select_best_server', cat='scheduler-waitpenalty')
        server_name = None
        difficulty = self.bitHopper.difficulty.get_difficulty()
        min_shares = difficulty * self.difficultyThreshold

        #self.bitHopper.log_dbg('min-shares: ' + str(min_shares), cat='scheduler-waitpenalty')  
        for server in self.bitHopper.pool.get_servers():
            shares,info = self.server_to_btc_shares(server)
            shares += float(info['wait']) * difficulty
            if info['api_lag'] or info['lag']:
                continue
            if info['role'] not in self.valid_roles:
                continue
            if shares < min_shares:
                min_shares = shares
                #self.bitHopper.log_dbg('Selecting pool ' + str(server) + ' with shares ' + str(info['shares']), cat='scheduler-waitpenalty')
                server_name = server
         
        if server_name == None:
            server_name = self.select_charity_server()

        if server_name == None:     
            server_name = self.select_backup_server()

        return server_name

    def server_update(self,):
        current = self.bitHopper.pool.get_current()
        shares,info = self.server_to_btc_shares(current)
        difficulty = self.bitHopper.difficulty.get_difficulty()

        if info['role'] not in self.valid_roles:
            return True
    
        if info['api_lag'] or info['lag']:
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
            self.bitHopper.log_dbg("Unable to set slicesize for defaultscheduler from a config file: " + str(e))
            pass

    def reset(self,):
        self.select_best_server()

    def select_best_server(self,):
        #self.bitHopper.log_dbg('select_best_server', cat='scheduler-default')
        difficulty = self.bitHopper.difficulty.get_difficulty()
        min_shares = difficulty * self.difficultyThreshold

        valid_servers = []
        for server in self.bitHopper.pool.get_servers():
            shares,info = self.server_to_btc_shares(server)
            if info['role'] not in self.valid_roles:
                continue

            if info['lag'] or info['api_lag']:
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
            return charity_server

        if valid_servers == []: 
            return self.select_backup_server()
      
        min_slice = self.sliceinfo[valid_servers[0]]
        server = valid_servers[0]
        for pool in valid_servers:
            info = self.bitHopper.pool.servers[pool]
            if info['api_lag'] or info['lag']:
                continue
            if self.sliceinfo[pool] <= min_slice:
                min_slice = self.sliceinfo[pool]
                server = pool
    
        return server

   
    def server_update(self,):
        #self.bitHopper.log_msg(str(self.sliceinfo))
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

        difficulty = self.bitHopper.difficulty.get_difficulty()
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
        self.bitHopper.log_msg('Initializing AltSliceScheduler...', cat=self.name)
        self.bitHopper.log_msg(' - Min Slice Size: ' + str(self.bitHopper.options.altminslicesize), cat=self.name)
        self.bitHopper.log_msg(' - Slice Size: ' + str(self.bitHopper.options.altslicesize), cat=self.name)
        self.lastcalled = time.time()
        self.target_duration = 0
        self.sbs_count = 0
        self.initDone = False
        self.reset()

    def reset(self,):
        for server in self.bitHopper.pool.get_servers():
            info = self.bitHopper.pool.get_entry(server)
            info['slice'] = -1
            info['slicedShares'] = 0
            if 'init' not in info:
                info['init'] = False
        if (self.bitHopper.options.altsliceroundtimebias == True):
            difficulty = self.bitHopper.difficulty.get_difficulty()
            one_ghash = 1000000 * 1000
            target_ghash = one_ghash * int(self.bitHopper.options.altsliceroundtimetarget) * self.difficultyThreshold
            self.bitHopper.log_msg(' - Target Round Time Bias GHash/s: ' + str(float(target_ghash/one_ghash)), cat=self.name)
            self.target_duration = difficulty * (2**32) / target_ghash
            self.bitHopper.log_msg(" - Target duration: " + str(int(self.target_duration)) + "(s) or " + str(int(self.target_duration/60)) + " minutes", cat=self.name)
            
    def select_best_server(self,):
        self.bitHopper.log_trace('select_best_server', cat=self.name)
        server_name = None
        difficulty = self.bitHopper.difficulty.get_difficulty()
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
                self.bitHopper.log_trace(server + " not yet initialized", cat=self.name)
                fullinit = False
            if 'init' not in info:
                fullinit = False
            shares = info['shares']
            if 'penalty' in info:
                shares = shares * float(info['penalty'])
            # favor slush over other pools if low enough
            if info['role'] in ['mine_c'] and shares * 4 < min_shares:
                fullinit = True
      
        if self.bitHopper.pool.get_current() == None or allSlicesDone == True:
            reslice = True
        elif self.bitHopper.pool.get_entry(current_server)['lag'] == True:
            reslice = True

        if (fullinit and self.initDone == False) or self.sbs_count > 64: # catch long init
            self.initDone = True
            reslice = True
         
        #self.bitHopper.log_dbg('allSlicesDone: ' + str(allSlicesDone) + ' fullinit: ' + str(fullinit) + ' initDone: ' + str(self.initDone), cat='reslice')
        if (reslice == True):
            self.bitHopper.log_msg('Re-Slicing...', cat=self.name)
            totalshares = 1
            totalweight = 0
            server_shares = {}
            for server in self.bitHopper.pool.get_servers():
                shares,info = self.server_to_btc_shares(server)
                shares += 1
                if info['role'] not in self.valid_roles:
                    continue
                if info['api_lag'] or info['lag']:
                    continue
                if shares < min_shares and shares >= 0:               
                    totalshares = totalshares + shares
                    info['slicedShares'] = shares
                    server_shares[server] = shares
                else:
                    self.bitHopper.log_trace(server + ' skipped ' + str(shares))
                    continue
            # find total weight
            for server in self.bitHopper.pool.get_servers():
                info = self.bitHopper.pool.get_entry(server)
                if info['role'] not in self.valid_roles:
                    continue
                if info['api_lag'] or info['lag']:
                    continue
                if server not in server_shares: continue
                if server_shares[server] < min_shares and server_shares[server] > 0:
                    totalweight += 1/(float(server_shares[server])/totalshares)
                      
                      
            # round time biasing
            tb_delta = {}
            tb_log_delta = {}
            pos_weight = {}
            neg_weight = {}
            adj_slice = {}
            # TODO punish duration estimates weighed by temporal duration
            if (self.bitHopper.options.altsliceroundtimebias == True):
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
                    self.bitHopper.log_trace('  ' + server + " delta: " + str(tb_delta[server]) + " log_delta: " + str(tb_log_delta[server]), cat=self.name)            

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
                self.bitHopper.log_trace("pos_total: " + str(pos_total) + " / neg_total: " + str(neg_total), cat=self.name)   
                
                # preslice            
                self.bitHopper.options.altslicesize
                for server in self.bitHopper.pool.get_servers():
                    if server in tb_delta:
                        info = self.bitHopper.pool.get_entry(server)
                        if info['isDurationEstimated'] == True and info['duration_temporal'] < 300:
                            tb_delta[server] = 0
                        else:
                            if tb_delta[server] >= 0:
                                pos_weight[server] = tb_log_delta[server] / pos_total
                                self.bitHopper.log_trace(server + " pos_weight: " + str(pos_weight[server]), cat=self.name)
                            elif tb_delta[server] < 0:
                                neg_weight[server] = tb_log_delta[server] / neg_total
                                self.bitHopper.log_trace(server + " neg_weight: " + str(neg_weight[server]), cat=self.name)
                                                    

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
                    self.bitHopper.log_trace('tb_delta: ' + str(len(tb_delta)) + ' / server_shares: ' + str(len(server_shares)), cat=self.name)
                    if (self.bitHopper.options.altsliceroundtimebias == True):
                        if len(tb_delta) == 1 and len(server_shares) == 1:
                            # only 1 server to slice (zzz)
                            if info['duration'] > 0:
                                slice = self.bitHopper.options.altslicesize
                            else:
                                slice = 0
                        else:
                            weight = 1/(float(shares)/totalshares)
                            slice = weight * self.bitHopper.options.altslicesize / totalweight
                            if self.bitHopper.options.altslicejitter != 0:
                                jitter = random.randint(0-self.bitHopper.options.altslicejitter, self.bitHopper.options.altslicejitter)
                                slice += jitter
                    else:                  
                        if shares == totalshares:
                            # only 1 server to slice (zzz)
                            slice = self.bitHopper.options.altslicesize
                        else:
                            weight = 1/(float(shares)/totalshares)
                            slice = weight * self.bitHopper.options.altslicesize / totalweight
                            if self.bitHopper.options.altslicejitter != 0:
                                jitter = random.randint(0-self.bitHopper.options.altslicejitter, self.bitHopper.options.altslicejitter)
                                slice += jitter
                    info['slice'] = slice
                    if self.bitHopper.options.debug:
                        self.bitHopper.log_dbg(server + " sliced to " + "{0:.2f}".format(info['slice']) + '/' + "{0:d}".format(int(self.bitHopper.options.altslicesize)) + '/' + str(shares) + '/' + "{0:.3f}".format(weight) + '/' + "{0:.3f}".format(totalweight) , cat=self.name)
                    else:
                        self.bitHopper.log_msg(server + " sliced to " + "{0:.2f}".format(info['slice']), cat=self.name)
                   
            # adjust based on round time bias
            if self.bitHopper.options.altsliceroundtimebias == True:
                self.bitHopper.log_dbg('Check if apply Round Time Bias: tb_log_delta: ' + str(len(tb_log_delta)) + ' == servers: ' + str(len(server_shares)), cat=self.name)
            if self.bitHopper.options.altsliceroundtimebias == True and len(tb_log_delta) >= 1:            
                self.bitHopper.log_msg('>>> Apply Round Time Bias === ', cat=self.name)
                ns_total = 0
                adj_factor = self.bitHopper.options.altsliceroundtimemagic
                self.bitHopper.log_trace('     server: ' + server)
                for server in self.bitHopper.pool.get_servers():
                    info = self.bitHopper.pool.get_entry(server)
                    if server not in tb_log_delta: continue # no servers to adjust
                    self.bitHopper.log_trace('     server(tld): ' + server)
                    if server in pos_weight:
                        adj_slice[server] = info['slice'] + adj_factor * pos_weight[server]
                        self.bitHopper.log_trace('     server (pos): ' + str(adj_slice[server]))
                        ns_total += adj_slice[server]            
                    elif server in neg_weight:                  
                        adj_slice[server] = info['slice'] - adj_factor * neg_weight[server]
                        self.bitHopper.log_trace('     server (neg): ' + str(adj_slice[server]))
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
                            info['slice'] = self.bitHopper.options.altslicesize * (adj_slice[server] / ad_totalslice)
                            if self.bitHopper.options.debug:
                                self.bitHopper.log_dbg(server + " _adjusted_ slice to " + "{0:.2f}".format(info['slice']) + '/' + "{0:d}".format(int(self.bitHopper.options.altslicesize)) + '/' + str(shares) + '/' + "{0:.3f}".format(adj_slice[server]) + '/' + "{0:.3f}".format(ad_totalslice) , cat=self.name)
                            else:
                                self.bitHopper.log_msg('  > ' + server + " _adjusted_ slice to " + "{0:.2f}".format(info['slice']) + " from {0:.2f}".format(previous), cat=self.name)
                        else:
                            info['slice'] = self.bitHopper.options.altslicesize * (info['slice'] / ad_totalslice)
                            if self.bitHopper.options.debug:
                                self.bitHopper.log_dbg(server + " sliced to " + "{0:.2f}".format(info['slice']) + '/' + "{0:d}".format(int(self.bitHopper.options.altslicesize)) + '/' + str(shares) + '/na/' + "{0:.3f}".format(ad_totalslice) , cat=self.name)
                            else:
                                self.bitHopper.log_msg(server + " sliced to " + "{0:.2f}".format(info['slice']), cat=self.name)
                                     
            # min share adjustment
            for server in self.bitHopper.pool.get_servers():
                info = self.bitHopper.pool.get_entry(server)
                if info['role'] not in self.valid_roles:
                    continue
                if info['shares'] < 0: continue
                if server not in server_shares: continue
                if info['slice'] < self.bitHopper.options.altminslicesize:
                    info['slice'] = self.bitHopper.options.altminslicesize
                    if self.bitHopper.options.debug:
                        self.bitHopper.log_dbg(server + " (min)sliced to " + "{0:.2f}".format(info['slice']) + '/' + "{0:d}".format(int(self.bitHopper.options.altslicesize)) + '/' + str(shares) + '/' + "{0:d}".format(info['duration']), cat=self.name)
                    else:
                        self.bitHopper.log_msg(server + " (min)sliced to " + "{0:.2f}".format(info['slice']), cat=self.name)                                           
   
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
            if info['role'] in self.valid_roles and info['slice'] > 0 and not info['lag']:
                if max_slice == -1:
                    max_slice = info['slice']
                    server_name = server
                if info['slice'] > max_slice:
                    max_slice = info['slice']
                    server_name = server
       
        if server_name == None: server_name = self.select_charity_server()
                   
        #self.bitHopper.log_dbg('server_name: ' + str(server_name), cat=self.name)
        if server_name == None:
            self.bitHopper.log_msg('No servers to slice, picking a backup...')
            server_name = self.select_backup_server()
        return server_name
         

    def server_update(self,):
        #self.bitHopper.log_dbg('server_update', cat='server_update')
        diff_time = time.time()-self.lastcalled
        self.lastcalled = time.time()
        current = self.bitHopper.pool.get_current()
        shares,info = self.server_to_btc_shares(current)
        info['slice'] = info['slice'] - diff_time
        #self.bitHopper.log_dbg(current_server + ' slice ' + str(info['slice']), cat='server_update' )
        if self.initDone == False:
            self.bitHopper.select_best_server()
            return True
        if info['slice'] <= 0: return True
          
        # shares are now less than shares at time of slicing (new block found?)
        if info['slicedShares'] > info['shares']:
            self.bitHopper.log_dbg("slicedShares > shares")
            return True
          
        # double check role
        if info['role'] not in self.valid_roles: return True
          
        # check to see if threshold exceeded
        difficulty = self.bitHopper.difficulty.get_difficulty()
        min_shares = difficulty * self.difficultyThreshold
    
        if shares > min_shares:
            self.bitHopper.log_dbg("shares > min_shares")
            info['slice'] = -1 # force switch
            return True
          
        return False

    def update_api_server(self,server):
        info = self.bitHopper.pool.get_entry(server)
        if info['role'] in ['info', 'disable'] and info['slice'] > 0:
            info['slice'] = -1
        return

