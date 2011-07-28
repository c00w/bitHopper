#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

class Scheduler(object):
   def __init__(self,bitHopper):
      self.bitHopper = bitHopper
      self.initData()
   
   @classmethod
   def initData(self,):
      print "<Scheduler> initData"
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
   def select_best_server(self,):
      return   
   def select_backup_server(self,):
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


