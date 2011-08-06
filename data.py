#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

class Data():
    def __init__(self,bitHopper):
        self.users = {}
        self.bitHopper = bitHopper
        self.pool = self.bitHopper.pool
        self.db = self.bitHopper.db
        self.speed = self.bitHopper.speed
        self.difficulty = self.bitHopper.difficulty
        self.db.update_user_shares_db()
        shares = self.db.get_user_shares()
        for user in shares:
            self.users[user] = {'shares':shares[user],'rejects':0, 'last':0}
        print self.users

    def get_users(self):
        users = {}
        for item in self.users:
            if self.users[item]['shares'] >0:
                users[item] = self.users[item]
        return users

    def user_share_add(self,user,password,shares,server):
        if user not in self.users:
            self.users[user] = {'shares':0,'rejects':0, 'last':0}
        self.users[user]['last'] = time.time()
        self.users[user]['shares'] += shares

    def reject_callback(self,server,data):
        try:
            if data != []:
                self.db.update_rejects(server,1)
                self.pool.get_servers()[server]['rejects'] += 1
        except Exception, e:
            self.bitHopper.log_dbg('reject_callback_error')
            self.bitHopper.log_dbg(str(e))
            return

    def data_callback(self,server,data, user, password):
        try:
            if data != []:
                self.speed.add_shares(1)
                self.db.update_shares(server, 1, user, password)
                self.pool.get_servers()[server]['user_shares'] +=1
                self.pool.get_servers()[server]['expected_payout'] += 1.0/self.difficulty.get_difficulty() * 50.0
                self.user_share_add(user, password, 1, server)

        except Exception, e:
            self.bitHopper.log_dbg('data_callback_error')
            self.bitHopper.log_dbg(str(e))
    
