#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import sqlite3
import os
import os.path
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

    def close(self):
        self.curs.close()

    def check_database(self):
        self.bitHopper.log_msg('Checking Database')
        if os.path.exists(DB_FN):
            try:
                versionfd = open(VERSION_FN, 'rb')
                version = versionfd.read()
                self.bitHopper.log_msg("DB Verson: " + version)
                if version != "0.1":
                    self.bitHopper.log_msg('Old Database')
                    os.remove(DB_FN)
                versionfd.close()
            except:
                os.remove(DB_FN)

        version = open(VERSION_FN, 'wb')
        version.write("0.1")
        version.close()
        
        self.database = sqlite3.connect(DB_FN)
        self.curs = self.database.cursor()
        
        for server_name in self.pool.get_servers():
            difficulty = self.bitHopper.difficulty.get_difficulty()
            sql = "CREATE TABLE IF NOT EXISTS "+server_name +" (diff REAL, shares INTEGER, rejects INTEGER, stored_payout REAL)"
            self.curs.execute(sql)
        
        for server in self.pool.get_servers():
            sql = 'select * from ' + server +' where diff = ' + str(difficulty)
            rows = self.curs.execute(sql)
            rows = rows.fetchall()
            if len(rows) == 0:
                sql = 'INSERT INTO ' + server + '(diff, shares, rejects, stored_payout) values( '+str(difficulty) +', '+str(0) +', '+str(0) + ', '+str(0)+ ')'
                self.curs.execute(sql)
        self.bitHopper.log_msg('Database Setup')

    def update_shares(self,server,shares):
        difficulty = self.bitHopper.difficulty.get_difficulty()
        sql = 'UPDATE '+ server +' SET shares= shares + '+ str(shares) +' WHERE diff='+ str(difficulty)
        self.curs.execute(sql)
        self.database.commit()

    def get_shares(self,server):
        sql = 'select shares from ' + str(server)
        self.curs.execute(sql)
        shares = 0
        for info in self.curs.fetchall():
            shares += int(info[0])
        return shares

    def update_rejects(self,server,shares):
        difficulty = self.bitHopper.difficulty.get_difficulty()
        sql = 'UPDATE '+ str(server) +' SET rejects= rejects + '+ str(shares) +' WHERE diff='+ str(difficulty)
        self.curs.execute(sql)
        self.database.commit()

    def get_rejects(self,server):
        sql = 'select rejects from ' + str(server)
        self.curs.execute(sql)
        shares = 0
        for info in self.curs.fetchall():
            shares += int(info[0])
        return shares
        
    def set_payout(self,server,payout):
        difficulty = self.bitHopper.difficulty.get_difficulty()
        sql = 'UPDATE '+ server +' Set stored_payout='+ str(payout) +' WHERE diff='+ str(difficulty)
        self.curs.execute(sql)
        self.database.commit()

    def get_payout(self,server):
        sql = 'select stored_payout from ' + server
        self.curs.execute(sql)
        payout = 0
        for info in self.curs.fetchall():
            payout += float(info[0])
        return payout
    
