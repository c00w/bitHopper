#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import os.path
import time
import random

from twisted.internet.task import LoopingCall
from twisted.web import server, resource

class Scheduler(object):
   def __init__(self,bitHopper):
      self.bh = bitHopper
      self.initData()

   @classmethod
   def initData(self,):
      #self.bh.log_msg("<Scheduler> initData")
      return

   @classmethod
   def server_update(self,):
      return

   @classmethod
   def select_best_server(self,):
      return

   @classmethod
   def select_friendly_server(self):
      return

   def select_latehop_server(self):
      server_name = None
      max_share_count = 1
      for server in self.bh.pool.get_servers():
         info = self.bh.pool.get_entry(server)
         if info['api_lag'] or info['lag']:
            continue
         if info['role'] != 'backup_latehop':
            continue
         if info['shares'] > max_share_count:
            server_name = server
            max_share_count = info['shares']
            #self.bh.log_dbg('select_latehop_server: ' + str(server), cat='scheduler-default')

      return server_name   

   def select_backup_server(self,):
      #self.bh.log_dbg('select_backup_server', cat='scheduler-default')
      server_name = self.select_latehop_server()
      reject_rate = 1      

      difficulty = self.bh.difficulty.get_difficulty()
      nmc_difficulty = self.bh.difficulty.get_nmc_difficulty()

      if server_name == None:
         for server in self.bh.pool.get_servers():
            info = self.bh.pool.get_entry(server)
            if info['role'] not in ['backup', 'backup_latehop']:
               continue
            if info['lag']:
               continue
            shares = info['user_shares']+1
            if 'penalty' in info:
               shares = shares * float(info['penalty'])
            rr_server = float(info['rejects'])/shares
            if rr_server < reject_rate:
               server_name = server
               self.bh.log_dbg('select_backup_server: ' + str(server), cat='select_backup_server')
               reject_rate = rr_server

      if server_name == None:
         #self.bh.log_dbg('Try another backup' + str(server), cat='scheduler-default')
         min_shares = 10**10
         for server in self.bh.pool.get_servers():
            info = self.bh.pool.get_entry(server)
            if info['api_lag'] or info['lag']:
                continue
            if info['role'] not in ['mine','mine_nmc','mine_slush']:
                continue
            if info['role'] == 'mine':
                shares = info['shares']
            elif info['role'] == 'mine_slush':
                shares = info['shares'] * 4
            elif info['role'] == 'mine_nmc':
                shares = info['shares']*difficulty / nmc_difficulty
            else:
                shares = info['shares']
            if 'penalty' in info:
               shares = shares * float(info['penalty'])
            if shares < min_shares and info['lag'] == False:
                min_shares = shares
                #self.bh.log_dbg('Selecting pool ' + str(server) + ' with shares ' + str(shares), cat='select_backup_server')
                server_name = server
      
      if server_name == None:
         #self.bh.log_dbg('Try another backup pt2' + str(server), cat='scheduler-default')
         for server in self.bh.pool.get_servers():
            info = self.bh.pool.get_entry(server)
            if info['role'] != 'backup':
               continue
            server_name = server
            break

      return server_name

   def update_api_server(self,server):
      return
   


class OldDefaultScheduler(Scheduler):
   def __init__(self,bitHopper):
      self.bh = bitHopper
      self.difficultyThreshold = 0.435
      self.initData()
      self.index_html = 'index-macboy.html'
      
   def initData(self,):
      if self.bh.options.threshold:
         #self.bh.log_msg("Override difficulty threshold to: " + str(self.bh.options.threshold), cat='scheduler-default')
         self.difficultyThreshold = self.bh.options.threshold

   def select_best_server(self,):
      #self.bh.log_dbg('select_best_server', cat='scheduler-default')
      server_name = None
      difficulty = self.bh.difficulty.get_difficulty()
      nmc_difficulty = self.bh.difficulty.get_nmc_difficulty()
      min_shares = difficulty * self.difficultyThreshold
        
      #self.bh.log_dbg('min-shares: ' + str(min_shares), cat='scheduler-default')  
      for server in self.bh.pool.get_servers():
         info = self.bh.pool.get_entry(server)
         if info['api_lag'] or info['lag']:
            continue
         if info['role'] not in ['mine','mine_nmc','mine_slush','mine_charity']:
            continue
         if info['role'] in ['mine', 'mine_charity']:
            shares = info['shares']
         elif info['role'] == 'mine_slush':
            shares = info['shares'] * 4
         elif info['role'] == 'mine_nmc':
            shares = info['shares']*difficulty / nmc_difficulty
         else:
            shares = 100* info['shares']
         # apply penalty
         if 'penalty' in info:
            shares = shares * float(info['penalty'])
         if shares< min_shares:
            min_shares = shares
            #self.bh.log_dbg('Selecting pool ' + str(server) + ' with shares ' + str(info['shares']), cat='scheduler-default')
            server_name = server
         
      if server_name == None:
         server_name = self.select_friendly_server()

      if server_name == None: return self.select_backup_server()
      else: return server_name   
   
   def select_friendly_server(self):
      server_name = None
      most_shares = self.bh.difficulty.get_difficulty() * 2
      for server in self.bh.pool.get_servers():
         info = self.bh.pool.get_entry(server)
         if info['role'] != 'mine_charity':
            continue
         if info['shares'] > most_shares and info['lag'] == False:
            server_name = server
            most_shares = info['shares']
            self.bh.log_dbg('select_friendly_server: ' + str(server), cat='scheduler-default')
      
      return server_name
   
   def select_latehop_server(self):
      server_name = None
      max_share_count = 1
      for server in self.bh.pool.get_servers():
         info = self.bh.pool.get_entry(server)
         if info['api_lag'] or info['lag']:
            continue
         if info['role'] != 'backup_latehop':
            continue
         if info['shares'] > max_share_count:
            server_name = server
            max_share_count = info['shares']
            self.bh.log_dbg('select_latehop_server: ' + str(server), cat='scheduler-default')

      return server_name   

   def server_update(self,):
      #self.bh.log_dbg('server_update', cat='scheduler-default')
      valid_roles = ['mine', 'mine_slush','mine_nmc']
      current_pool = self.bh.pool.get_entry(self.bh.pool.get_current())
      if current_pool['role'] not in valid_roles:
         return True
    
      if current_pool['api_lag'] or current_pool['lag']:
         return True

      current_role = current_pool['role']
      if current_role == 'mine' or current_role == 'mine_charity':
         difficulty = self.bh.difficulty.get_difficulty()
      if current_role == 'mine_nmc':
         difficulty = self.bh.difficulty.get_nmc_difficulty()
      if current_role == 'mine_slush':
         difficulty = self.bh.difficulty.get_difficulty() * .25
      if 'penalty' in current_pool:
         difficulty = self.bh.difficulty.get_difficulty() / float(current_pool['penalty'])
      if current_pool['shares'] > (difficulty * self.difficultyThreshold):
         return True

      min_shares = 10**10

      for server in self.bh.pool.get_servers():
         pool = self.bh.pool.get_entry(server)
         if pool['shares'] < min_shares:
            min_shares = pool['shares']

      if min_shares < current_pool['shares']*.90:
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


class DefaultScheduler(Scheduler):
   def __init__(self,bitHopper):
      self.bh = bitHopper
      self.bitHopper = self.bh
      self.difficultyThreshold = 0.435
      self.sliceinfo = {}
      self.initData()
      self.lastcalled = time.time()
      self.index_html = 'index-slice.html'
      call = LoopingCall(self.bh.server_update)
      call.start(10)
   def initData(self,):
        if self.bh.options.threshold:
         #self.bh.log_msg("Override difficulty threshold to: " + str(self.bh.options.threshold), cat='scheduler-default')
         self.difficultyThreshold = self.bh.options.threshold
        for server in self.bh.pool.get_servers():
            self.sliceinfo[server] = -1

   def select_best_server(self,):
      #self.bh.log_dbg('select_best_server', cat='scheduler-default')
      server_name = None
      difficulty = self.bh.difficulty.get_difficulty()
      nmc_difficulty = self.bh.difficulty.get_nmc_difficulty()
      min_shares = difficulty * self.difficultyThreshold

      valid_servers = []
      for server in self.bh.pool.get_servers():
         info = self.bh.pool.get_entry(server)
         if info['api_lag'] or info['lag']:
            continue
         if info['role'] not in ['mine','mine_nmc','mine_slush']:
            continue
         if info['role'] in ['mine']:
            shares = info['shares']
         elif info['role'] == 'mine_slush':
            shares = info['shares'] * 4
         elif info['role'] == 'mine_nmc':
            shares = info['shares']*difficulty / nmc_difficulty
         else:
            shares = 100* info['shares']
         # apply penalty
         if 'penalty' in info:
            shares = shares * float(info['penalty'])
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

      if valid_servers == []: return self.select_backup_server()
      
      min_slice = self.sliceinfo[valid_servers[0]]
      server = valid_servers[0]
      for pool in valid_servers:
        if self.sliceinfo[pool] < min_slice:
            min_slice = self.sliceinfo[pool]
            server = pool

      return server

   def server_update(self,):
        #self.bitHopper.log_msg(str(self.sliceinfo))
        diff_time = time.time()-self.lastcalled
        self.lastcalled = time.time()
        current = self.sliceinfo[self.bh.pool.get_current()]
        if current == -1:
            return True

        if self.bh.pool.servers[self.bh.pool.get_current()]['role'] not in ['mine','mine_charity','mine_slush','mine_nmc']:
            return True

        self.sliceinfo[self.bh.pool.get_current()] += diff_time

        valid = []
        for k in self.sliceinfo:
            if self.sliceinfo[k] != -1:
                valid.append(k)

        if len(valid) <=1:
            return True

        for server in valid:
            if current - self.sliceinfo[server] > 30:
                return True

        difficulty = self.bh.difficulty.get_difficulty()
        nmc_difficulty = self.bh.difficulty.get_nmc_difficulty()
        min_shares = difficulty * self.difficultyThreshold

        info = self.bh.pool.servers[self.bh.pool.get_current()]
        if info['role'] in ['mine']:
           shares = info['shares']
        elif info['role'] == 'mine_slush':
           shares = info['shares'] * 4
        elif info['role'] == 'mine_nmc':
           shares = info['shares']*difficulty / nmc_difficulty
        else:
           shares = 100* info['shares']
        if 'penalty' in info:
            shares = shares * float(info['penalty'])
        if shares > mine_shares:
            return True

        return False

class AltSliceScheduler(Scheduler):
   def __init__(self,bitHopper):
      self.bh = bitHopper
      self.bitHopper = self.bh
      self.difficultyThreshold = 0.435
      self.sliceinfo = {}
      self.name = 'scheduler-altslice'
      self.bh.log_msg('Initializing AltSliceScheduler...', cat=self.name)
      self.bh.log_msg(' - Min Slice Size: ' + str(self.bh.options.altminslicesize), cat=self.name)
      self.bh.log_msg(' - Slice Size: ' + str(self.bh.options.altslicesize), cat=self.name)
      self.initData()
      self.lastcalled = time.time()
      self.index_html = 'index-altslice.html'
      
      self.initDone = False
      
   def initData(self,):
        if self.bh.options.threshold:
         #self.bh.log_msg("Override difficulty threshold to: " + str(self.bh.options.threshold), cat='scheduler-default')
         self.difficultyThreshold = self.bh.options.threshold
        for server in self.bh.pool.get_servers():
            info = self.bh.pool.get_entry(server)
            info['slice'] = -1
            info['slicedShares'] = 0
            info['init'] = False

   def select_best_server(self,):
      self.bh.log_dbg('select_best_server', cat=self.name)
      server_name = None
      difficulty = self.bh.difficulty.get_difficulty()
      nmc_difficulty = self.bh.difficulty.get_nmc_difficulty()
      min_shares = difficulty * self.difficultyThreshold

      current_server = self.bh.pool.get_current()
      reslice = True
      fullinit = True
      allSlicesDone = True
      
      for server in self.bh.pool.get_servers():
         info = self.bh.pool.get_entry(server)
         if info['slice'] > 0:
            reslice = False
            allSlicesDone = False
         if info['init'] == False and info['role'] in ['mine','mine_nmc','mine_slush']:
            #self.bh.log_dbg(server + " not yet initialized", cat=self.name)
            fullinit = False
      
      if self.bh.pool.get_current() == None or allSlicesDone == True:
         reslice = True
      elif self.bh.pool.get_entry(current_server)['lag'] == True:
         reslice = True

      if fullinit and self.initDone == False:
         self.initDone = True
         reslice = True
         
      #self.bh.log_dbg('allSlicesDone: ' + str(allSlicesDone) + ' fullinit: ' + str(fullinit) + ' initDone: ' + str(self.initDone), cat='reslice')
      if (reslice == True):
         self.bh.log_msg('Re-Slicing...', cat=self.name)
         totalshares = 0
         totalweight = 0
         server_shares = {}
         for server in self.bh.pool.get_servers():
            info = self.bh.pool.get_entry(server)
            if info['role'] not in ['mine','mine_nmc','mine_slush']:
               continue
            if info['api_lag'] or info['lag']:
               continue
            if info['role'] in ['mine']:
               shares = info['shares']
            elif info['role'] == 'mine_slush':
               shares = info['shares'] * 4
            elif info['role'] == 'mine_nmc':
               shares = info['shares']*difficulty / nmc_difficulty
            else:
               shares = 100* info['shares']
            # apply penalty
            if 'penalty' in info:
               shares = shares * float(info['penalty'])
            if shares < min_shares and shares > 0:               
               totalshares = totalshares + shares               
               info['slicedShares'] = info['shares']
               server_shares[server] = shares
            else:
               #self.bh.log_dbg(server + ' skipped ')
               continue
            
         # find total weight   
         for server in self.bh.pool.get_servers():
            info = self.bh.pool.get_entry(server)
            if info['role'] not in ['mine','mine_nmc','mine_slush']:
               continue
            if info['api_lag'] or info['lag']:
               continue
            if info['role'] in ['mine']:
               shares = info['shares']
            elif info['role'] == 'mine_slush':
               shares = info['shares'] * 4
            elif info['role'] == 'mine_nmc':
               shares = info['shares']*difficulty / nmc_difficulty
            else:
               shares = 100* info['shares']
            # apply penalty
            if 'penalty' in info:
               shares = shares * float(info['penalty'])
            if shares < min_shares and shares > 0:                        
               totalweight += 1/(float(shares)/totalshares)
                  
         # allocate slices         
         for server in self.bh.pool.get_servers():
            info = self.bh.pool.get_entry(server)
            if info['role'] not in ['mine','mine_nmc','mine_slush']:
               continue
            if info['shares'] <=0: continue
            if server not in server_shares:
               continue
            shares = server_shares[server] + 1
            if shares < min_shares and shares > 0:
               weight = 0
               if shares == totalshares:
                  # only 1 server to slice (zzz)
                  slice = self.bh.options.altslicesize
               else:
                  weight = 1/(float(shares)/totalshares)
                  slice = weight * self.bh.options.altslicesize / totalweight
                  if self.bh.options.altslicejitter != 0:
                     jitter = random.randint(0-self.bh.options.altslicejitter, self.bh.options.altslicejitter)
                     slice += jitter
               if slice < self.bh.options.altminslicesize: info['slice'] = self.bh.options.altminslicesize
               else: info['slice'] = slice               
               self.bh.log_msg(server + " sliced to " + "{0:.2f}".format(info['slice']) + '/' + "{0:d}".format(int(self.bh.options.altslicesize)) + '/' + str(shares) + '/' + "{0:.3f}".format(weight) + '/' + "{0:.3f}".format(totalweight) , cat=self.name)
   
      # Pick server with largest slice first
      max_slice = -1
      for server in self.bh.pool.get_servers():
         info = self.bh.pool.get_entry(server)
         if info['role'] in ['mine','mine_nmc','mine_slush'] and info['slice'] > 0 and info['lag'] == False:
            if max_slice == -1:
               max_slice = info['slice']
               server_name = server
            if info['slice'] > max_slice:
               server_name = server
            
      #self.bh.log_dbg('server_name: ' + str(server_name), cat=self.name)
      if server_name == None: server_name = self.select_backup_server()
      return server_name
         

   def server_update(self,):
      #self.bh.log_dbg('server_update', cat='server_update')
      diff_time = time.time()-self.lastcalled
      self.lastcalled = time.time()
      current_server = self.bh.pool.get_current()
      info = self.bh.pool.get_entry(current_server)
      info['slice'] = info['slice'] - diff_time
      #self.bh.log_dbg(current_server + ' slice ' + str(info['slice']), cat='server_update' )
      if self.initDone == False:
         self.bh.select_best_server()
         return True
      if info['slice'] <= 0: return True
      
      # shares are now less than shares at time of slicing (new block found?)
      if info['slicedShares'] > info['shares']: return True
      
      # double check role
      if info['role'] not in ['mine','mine_nmc','mine_slush']: return True
      
      # check to see if threshold exceeded
      difficulty = self.bh.difficulty.get_difficulty()
      shares = info['shares']
      min_shares = difficulty * self.difficultyThreshold
      if info['role'] == 'mine_slush': shares = shares * 4
      if 'penalty' in info: shares = shares * float(info['penalty'])
      if shares > min_shares:
         info['slice'] = -1 # force switch
         return True
      
      return False

   def update_api_server(self,server):
      info = self.bh.pool.get_entry(server)
      if info['role'] in ['info', 'disable'] and info['slice'] > 0:
         info['slice'] = -1
      return

