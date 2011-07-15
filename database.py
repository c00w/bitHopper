#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import sqlite3
import pool
import diff

curs = None

def check_database():
    print 'Checking Database'
    global curs
    database = sqlite3.connect('stats.db')
    curs = database.cursor()
    
    for server_name in pool.get_servers():
        sql = "CREATE TABLE IF NOT EXISTS "+server_name +" (diff REAL, shares INTEGER, stored_payout REAL)"
        curs.execute(sql)
    
    for server in pool.get_servers():
        sql = 'select * from ' + server +' where diff = ' + str(diff.difficulty)
        rows = curs.execute(sql)
        rows = rows.fetchall()
        if len(rows) == 0:
            sql = 'INSERT INTO ' + server + '(diff,shares,stored_payout, stored_money) values( '+str(diff.difficulty) +', '+str(0) + ', '+str(0)+ ')'
            curs.execute(sql)
    print 'Database Setup'

def update_database(server,shares):

    sql = 'UPDATE '+ server +'Set shares= shares + '+ shares +' WHERE diff='+ diff.difficulty
    curs.execute(sql)
    
    
    
