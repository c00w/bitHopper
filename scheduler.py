#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import os.path

from twisted.web import server, resource

class Scheduler(object):
   def __init__(self,bitHopper):
      self.bh = bitHopper
      self.initData()

   def initData(self,):
      self.bh.log_msg("<Scheduler> initData")
      return

   @classmethod
   def server_update(self,):
      return

   @classmethod
   def select_best_server(self,):
      return

   @classmethod
   def select_backup_server(self,):
      return


class DefaultScheduler(Scheduler):
   def __init__(self,bitHopper):
      self.bh = bitHopper
      self.difficultyThreshold = 0.43
      self.initData()
      
   def initData(self,):
      if self.bh.options.threshold:
         self.bh.log_msg("Override difficulty threshold to: " + str(self.bh.options.threshold), cat='scheduler-default')
         self.difficultyThreshold = self.bh.options.threshold

   def select_best_server(self,):
      self.bh.log_dbg('select_best_server', cat='scheduler-default')
      server_name = None
      difficulty = self.bh.difficulty.get_difficulty()
      nmc_difficulty = self.bh.difficulty.get_nmc_difficulty()
      min_shares = difficulty * self.difficultyThreshold
        
      self.bh.log_dbg('min-shares: ' + str(min_shares), cat='scheduler-default')  
      for server in self.bh.pool.get_servers():
         info = self.bh.pool.get_entry(server)
         info['shares'] = int(info['shares'])
         if info['role'] not in ['mine','mine_nmc','mine_slush']:
            continue
         if info['role'] == 'mine':
            shares = info['shares']
         elif info['role'] == 'mine_slush':
            shares = info['shares'] * 4
         elif info['role'] == 'mine_nmc':
            shares = info['shares']*difficulty / nmc_difficulty
         else:
            shares = 100* info['shares']
         if shares< min_shares and info['lag'] == False:
            min_shares = shares
            self.bh.log_dbg('Selecting pool ' + str(server) + ' with shares ' + str(info['shares']), cat='scheduler-default')
            server_name = server
         
      if server_name == None: return self.select_backup_server()
      else: return server_name   
   
   def select_backup_server(self,):
      self.bh.log_dbg('select_backup_server', cat='scheduler-default')
      server_name = None
      reject_rate = 1
      for server in self.bh.pool.get_servers():
         info = self.bh.pool.get_entry(server)
         if info['role'] != 'backup':
            continue
         if info['lag'] == False:
            rr_server = float(info['rejects'])/(info['user_shares']+1)
            if  rr_server < reject_rate:
               server_name = server
               self.bh.log_dbg('select_backup_server: ' + str(server), cat='scheduler-default')
               reject_rate = rr_server

   
      if server_name == None:
         self.bh.log_dbg('Try another backup' + str(server), cat='scheduler-default')
         min_shares = 10**10
         for server in self.bh.pool.get_servers():
            info = self.bh.pool.get_entry(server)
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
            if shares < min_shares and info['lag'] == False:
               min_shares = shares
               self.bh.log_dbg('Selecting pool ' + str(server) + ' with shares ' + str(shares), cat='scheduler-default')
               server_name = server
      
      if server_name == None:
         self.bh.log_dbg('Try another backup pt2' + str(server), cat='scheduler-default')
         for server in self.bh.pool.get_servers():
            info = self.bh.pool.get_entry(server)
            if info['role'] != 'backup':
               continue
            server_name = server
            break
         
      return server_name


   def server_update(self,):
      self.bh.log_dbg('server_update', cat='scheduler-default')
      valid_roles = ['mine', 'mine_slush','mine_nmc']
      current_pool = self.bh.pool.get_entry(self.bh.pool.get_current())
      if current_pool['role'] not in valid_roles:
         self.select_best_server()
         return

      current_role = current_pool['role']
      if current_role == 'mine':
         difficulty = self.bh.difficulty.get_difficulty()
      if current_role == 'mine_nmc':
         difficulty = self.bh.difficulty.get_nmc_difficulty()
      if current_role == 'mine_slush':
         difficulty = self.bh.difficulty.get_difficulty() * 4
      if current_pool['shares'] > (difficulty * self.difficultyThreshold):
         self.select_best_server()
         return

      min_shares = 10**10

      for server in self.bh.pool.get_servers():
         pool = self.bh.pool.get_entry(server)
         if pool['shares'] < min_shares:
            min_shares = pool['shares']

      if min_shares < current_pool['shares']*.90:
         self.select_best_server()
         return      

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


class SliceScheduler(Scheduler):
   def select_best_server(self,):
      return
   def select_backup_server(self,):
      return
