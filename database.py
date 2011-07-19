#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import sqlite3
import diff


class Database():
    def __init__(self,bitHopper):
        self.curs = None
        self.bitHopper = bitHopper
        self.pool = bitHopper.pool
        self.check_database()

    def check_database(self):
        print 'Checking Database'
        database = sqlite3.connect('stats.db')
        self.curs = database.cursor()
        
        for server_name in self.pool.get_servers():
            sql = "CREATE TABLE IF NOT EXISTS "+server_name +" (diff REAL, shares INTEGER, stored_payout REAL)"
            self.curs.execute(sql)
        
        for server in self.pool.get_servers():
            sql = 'select * from ' + server +' where diff = ' + str(diff.difficulty)
            rows = self.curs.execute(sql)
            rows = rows.fetchall()
            if len(rows) == 0:
                sql = 'INSERT INTO ' + server + '(diff,shares,stored_payout) values( '+str(diff.difficulty) +', '+str(0) + ', '+str(0)+ ')'
                self.curs.execute(sql)
        print 'Database Setup'

    def update_shares(self,server,shares):

        sql = 'UPDATE '+ server +'Set shares= shares + '+ shares +' WHERE diff='+ diff.difficulty
        self.curs.execute(sql)

    def get_shares(self,server,shares):
        sql = 'select shares from ' + server
        self.curs.execute(sql)
        shares = 0
        for info in self.curs.fetchall():
            shares += int(info[0])
        return shares
        
    def update_payout(self,server,payout):

        sql = 'UPDATE '+ server +'Set stored_payout= stored_payout + '+ payout +' WHERE diff='+ diff.difficulty
        self.curs.execute(sql)

    def get_payout(self,server,shares):
        sql = 'select stored_payout from ' + server
        self.curs.execute(sql)
        payout = 0
        for info in self.curs.fetchall():
            payout += float(info[0])
        return payout
    
