#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import sqlite3
import os
import os.path

from twisted.internet.task import LoopingCall

try:
    DB_DIR = os.path.dirname(os.path.abspath(__file__))
except:
    DB_DIR = os.curdir()

VERSION_FN = os.path.join(DB_DIR, 'db-version')
DB_FN = os.path.join(DB_DIR, 'stats.db')

class Database():
    def __init__(self,bitHopper):
        self.curs = None
        self.bitHopper = bitHopper
        self.pool = bitHopper.pool
        self.check_database()
        
        self.shares = {}
        self.rejects = {}
        self.payout = {}

        call = LoopingCall(self.write_database)
        call.start(60)

    def close(self):
        self.curs.close()

    def write_database(self):
        self.bitHopper.log_msg('writing to database')

        difficulty = self.bitHopper.difficulty.get_difficulty()
        for server in self.shares:
            for user in self.shares[server]:
                shares = self.shares[server]
                sql = 'UPDATE '+ str(server) +' SET shares= shares + '+ str(shares) +' WHERE diff='+ str(difficulty) + ' and user=' + str(user)
                self.curs.execute(sql)
                self.shares[server][user] = 0

        for server in self.rejects:
            rejects = self.rejects[server]
            sql = 'UPDATE '+ str(server) +' SET rejects= rejects + '+ str(rejects) +' WHERE diff='+ str(difficulty)
            self.curs.execute(sql)
            self.rejects[server] = 0

        for server in self.payout:
            payout = self.payout[server]
            sql = 'UPDATE '+ str(server) +' SET payout= '+ str(payout) +' WHERE diff='+ str(difficulty)
            self.curs.execute(sql)
            self.payout[server] = 0

        self.database.commit()
        
    def check_database(self):
        self.bitHopper.log_msg('Checking Database')
        if os.path.exists(DB_FN):
            try:
                versionfd = open(VERSION_FN, 'rb')
                version = versionfd.read()
                self.bitHopper.log_msg("DB Verson: " + version)
                if version == "0.1":
                    self.bitHopper.log_msg('Old Database')
                versionfd.close()
            except:
                os.remove(DB_FN)

        version = open(VERSION_FN, 'wb')
        version.write("0.2")
        version.close()
        
        self.database = sqlite3.connect(DB_FN)
        self.curs = self.database.cursor()

        if version == "0.1":
            sql = "SELECT name FROM sqlite_master WHERE type='table'"
            self.curs.execute(sql)
            result = self.curs.fetchall()
            for item in result:
                sql = "ALTER TABLE " + item[0] + " ADD COLUMN user TEXT"
                self.curs.execute(sql)
        
        for server_name in self.pool.get_servers():
            difficulty = self.bitHopper.difficulty.get_difficulty()
            sql = "CREATE TABLE IF NOT EXISTS "+server_name +" (diff REAL, shares INTEGER, rejects INTEGER, stored_payout REAL,  user TEXT)"
            self.curs.execute(sql)

        self.database.commit()
        
        self.bitHopper.log_msg('Database Setup')

    def update_shares(self,server, shares, user, password):
        if server not in self.shares:
            self.shares[server] = {}
        if user not in self.shares[server]:
            self.shares[server][user] = 0
        self.shares[server][user] += shares

    def get_shares(self,server):
        sql = 'select shares from ' + str(server)
        self.curs.execute(sql)
        shares = 0
        for info in self.curs.fetchall():
            shares += int(info[0])
        return shares

    def update_rejects(self,server,shares):
        if server not in self.rejects:
            self.rejects[server] = 0
        self.rejects[server] += shares

    def get_rejects(self,server):
        sql = 'select rejects from ' + str(server)
        self.curs.execute(sql)
        shares = 0
        for info in self.curs.fetchall():
            shares += int(info[0])
        return shares
        
    def set_payout(self,server,payout):
        if server not in self.payout:
            self.payout[server] = 0
        self.payout[server] = payout

    def get_payout(self,server):
        sql = 'select stored_payout from ' + server
        self.curs.execute(sql)
        payout = 0
        for info in self.curs.fetchall():
            payout += float(info[0])
        return payout
    
