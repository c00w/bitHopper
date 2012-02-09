#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import os, threading, socket
import sqlite3, logging, sys, time, gevent

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

try:
    # determine if application is a script file or frozen exe
    if hasattr(sys, 'frozen'):
        DB_DIR = os.path.dirname(sys.executable)
    else:
        DB_DIR = os.path.dirname(os.path.abspath(__file__))
except:
    DB_DIR = os.curdir
    

VERSION_FN = os.path.join(DB_DIR, 'db-version')
DB_FN = os.path.join(DB_DIR, 'stats.db')

class Database():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.curs = None
        self.pool = bitHopper.pool
        self.shares = {}
        self.rejects = {}
        self.payout = {}
        self.alive = True
        self.lock = threading.Lock()
        self.lock.acquire()
        thread = threading.Thread(target=self.__thread_init)
        thread.daemon = True
        thread.start()
        
    def _lock_get(self, user=""):
        while not self.lock.acquire(False):
            gevent.sleep(0)
        #print 'Lock Acquired' + user
            
    def _lock_release(self):
        self.lock.release()
        #print 'Lock Released'
        
    def __thread_init(self):
        self.check_database()
        self.lock.release()
        self.write_database()
        

    def close(self):
        self.curs.close()

    def sql_insert(self, server, shares=0, rejects=0, payout=0, user='', diff=None):
        if diff == None:
            difficulty = self.bitHopper.difficulty['btc']
        else:
            difficulty = diff
        sql = 'INSERT INTO ' + server + ' VALUES ( ' + str(difficulty) + ',' + str(shares) + ',' + str(rejects) + ',' + str(payout) + ',\'' + user + '\')'
        return sql

    def sql_update_add(self, server, value, amount, user):
        difficulty = self.bitHopper.difficulty['btc']
        sql = 'UPDATE ' + str(server) + ' SET ' + value + ' = ' + value + ' + ' + str(amount) + ' WHERE diff = ' + str(difficulty) + ' and user = \'' + user + "\'"
        return sql

    def sql_update_set(self, server, value, amount, user, difficulty):
        sql = 'UPDATE ' + str(server) + ' SET ' + value + ' = ' + str(amount) + ' WHERE diff = ' + str(difficulty) + ' and user = \'' + user + "\'"
        return sql

    def write_database(self):
        count = 0
        while self.alive:
            count +=1
            if self.pool == None:
                time.sleep(60)
                continue
            with self.lock:
            
                #Vacuum once per hour to help deal with
                #Sqlite performance issues.
                if count > 60:
                    self.curs.execute('VACUUM')
                    count = 0
                logging.info('DB: writing to database')

                for server_name in self.pool.get_servers():
                    self.make_table(server_name)

                difficulty = self.bitHopper.difficulty['btc']
                for server in self.shares:
                    for user in self.shares[server]:
                        if self.shares[server][user] == 0:
                            continue
                        shares = self.shares[server][user]
                        sql = self.sql_update_add(server,'shares',shares,user)
                        self.curs.execute(sql)
                        if len(self.curs.execute('select * from ' + server + '  WHERE diff='+ str(difficulty) + ' and user= \'' + str(user) + "\'").fetchall()) == 0:
                            sql = self.sql_insert(server,shares=shares,user=user)
                            self.curs.execute(sql)
                        self.shares[server][user] = 0

                for server in self.rejects:
                    for user in self.rejects[server]:
                        if self.rejects[server][user] == 0:
                            continue
                        rejects = self.rejects[server][user]
                        sql = self.sql_update_add(server,'rejects',rejects,user)
                        self.curs.execute(sql)
                        if len(self.curs.execute('select * from ' + server + '  WHERE diff='+ str(difficulty) + ' and user= \'' + str(user) + "\'").fetchall()) == 0:
                            sql = self.sql_insert(server,rejects=rejects,user=user)
                            self.curs.execute(sql)
                        self.rejects[server][user] = 0

                for server in self.payout:
                    if self.payout[server] == None:
                        continue
                    payout = self.payout[server]
                    sql = self.sql_update_set(server,'stored_payout', payout,'',1)
                    self.curs.execute(sql)
                    if len(self.curs.execute('select * from ' + server + '  WHERE diff='+ str(1) + ' and user= \'\'').fetchall()) == 0:
                        sql = self.sql_insert(server,payout=payout,diff=1)
                        self.curs.execute(sql)
                    self.payout[server] = None
                
            self.database.commit()
            time.sleep(60)

    def check_database(self):
        logging.info('Cleaning Database')

        self.database = sqlite3.connect(DB_FN, check_same_thread = False)
        self.curs = self.database.cursor()
        self.curs.execute("VACUUM")

        self.database.commit()

    def get_users(self):
        """
        Get a dictionary of user information to seed data.py
        This is a direct database lookup and should only be called once
        """
        self._lock_get('get_users')
        
        users = {}
        servers = self.bitHopper.pool.get_servers()
        for server in servers:
            sql = 'select user, shares, rejects from ' + server
            self.curs.execute(sql)
            result = self.curs.fetchall()
            for item in result:
                if item[0] not in users:
                    users[item[0]] = {'shares':0,'rejects':0}
                users[item[0]]['shares'] += item[1]
                users[item[0]]['rejects'] += item[2]
        self._lock_release()
        return users

    def update_shares(self, server, shares, user, password):
        self._lock_get('update_shares')
            
        if server not in self.shares:
            self.shares[server] = {}
        if user not in self.shares[server]:
            self.shares[server][user] = 0
        self.shares[server][user] += shares
        self._lock_release()
        
    def get_shares(self, server):
        self._lock_get('get_shares')
        sql = 'select shares from ' + str(server)
        self.curs.execute(sql)
        shares = 0
        for info in self.curs.fetchall():
            shares += int(info[0])
        self._lock_release()
        return shares

    def expected_payout_dict_expander(self, sharesDict, dictKey, user, diff):
        sharesDict[dictKey]['user'].append(user)
        sharesDict[dictKey]['diff'].append(diff)
        return sharesDict

    def expected_payout_sql_updater(self, server, sharesDict, shares, diffListSeek = 0, shareStepList = [], rejectsMode = False):
        """
        Updates pools table with user shares and rejects from data specified in
        sharesDict{} format. If specified can add extra shares from shareStepList[] to
        shares found from sharesDict{}.

        Returns how many shares in total got added to the database from
        sharesDict/rejectsDict

        sharesDict/rejectsDict template:
        sharesDict = { 9.0313: {'user': [user], 'diff': [diff]} }
        or
        sharesDict = { 9.0313: {'user': [user1, user2, user3], 'diff': [diff1, diff2, diff3]}

        """
        listIterator = 0
        newDbSharesTotal = 0
        for diff in sharesDict[shares]['diff']:
            shareAmount = shares

            if diffListSeek > 0:
                shareAmount += shareStepList[listIterator]
                diffListSeek -= 1

            if not rejectsMode:
                value = 'shares'
            else:
                value = 'rejects'

            sql = self.sql_update_set(server, value=value, amount=int(shareAmount), user=sharesDict[shares]['user'][listIterator], difficulty=diff)
            #print server, 'value=' + str(value), 'amount=' + str(int(shareAmount)), 'user=' + str(sharesDict[shares]['user'][listIterator]), 'difficulty=' + str(diff) 
            self._lock_get('expected_payout_sql_updater')
            self.curs.execute(sql)
            self._lock_release()

            listIterator += 1
            newDbSharesTotal += int(shareAmount)
        return newDbSharesTotal

    def expected_payout_share_modifier(self, payoutDifference, sharesDict, shares, loopsRequired, newExpPayoutTotal, newDbSharesTotal, server, addShares):
        """
        Checks if expected payout that was initially specified is different from the one
        that we got when increasing/decreasing shares percentually. If payout is
        different then increase of decrease shares using "share step" which is a
        share multiplier to make share increase/decrease be able to get rid of payout
        difference. This is probably the most important code related to changing
        expected payout.
        """
        diffListSeek = 0
        shareStepList = []
        if payoutDifference > 0:
            for diff in sharesDict[shares]['diff']:
                shareStepWorth = loopsRequired / float(diff) * 50
                if payoutDifference - shareStepWorth > 0:
                    if addShares:
                        shareStepList.append(loopsRequired)
                        newExpPayoutTotal += shareStepWorth
                    else:
                        shareStepList.append(-loopsRequired)
                        newExpPayoutTotal -= shareStepWorth
                    diffListSeek += 1
                    payoutDifference -= shareStepWorth
                else:
                    if loopsRequired > 1:
                        shareCount = 0
                        singleShareWorth = 1 / float(diff) * 50
                        for _ in range(loopsRequired):
                            if payoutDifference - singleShareWorth > 0:
                                shareCount += 1
                                if addShares:
                                    newExpPayoutTotal += singleShareWorth
                                else:
                                    newExpPayoutTotal -= singleShareWorth
                                payoutDifference -= singleShareWorth
                            else:
                                payoutDifference = 0
                                if not addShares:
                                    shareCount += 1 # This is required to make payout 1 share smaller than specified instead of 1 share bigger
                                    newExpPayoutTotal -= singleShareWorth
                                break
                        if not addShares:
                            shareCount = shareCount * -1
                        diffListSeek += 1
                        shareStepList.append(shareCount)
                    else:
                        payoutDifference = 0
                        if not addShares:
                            shareStepList.append(-loopsRequired) # This is required to make payout loopsRequired shares smaller than specified instead of 1 share bigger
                            newExpPayoutTotal -= shareStepWorth
                            diffListSeek += 1
                        break
        else:
            pass
        newDbSharesTotal += self.expected_payout_sql_updater(server, sharesDict, shares, diffListSeek, shareStepList=shareStepList)
        return payoutDifference, newExpPayoutTotal, newDbSharesTotal

    def change_expected_payout(self, server, requiredSharesTotal, expectedPayout):
        """
        Makes it possible to store expected payout changes in the database. Since
        modifying payouts for existing users isn't very straightforward
        then the entered expected payout number might not match with the
        number derived from here completely. It will be as close as possible 
        though.

        Shares get increased/decreased percentually. Since input share numbers are integers
        then newly derived floating share numbers that we get from multiplying with percentage
        will need to get rounded properly. Even after rounding these shares there could be problems
        because user shares can come with various Bitcoin difficulties and because of that can
        have different expected payout values.

        Besides correcting expected payout you can also just set expected payout to 0 if you have
        cleared pools balance.

        Another thing to note is that if you specify expected payout for a pool that has got no
        user shares then this method will get total share counts for all users to determine
        how many shares percentually to give to each user.

        TODO: This code is already pretty throughly tested over last few weeks but obviously it
        requires some code cleanup. Before I go ahead I would like to verify that nobody has
        any bugs with this implementation though.

        sdogi 21.09.2011

        """
        self._lock_get(user="change expected payout")
        try:
            if server in self.shares:
                for user in self.shares[server]:
                    self.shares[server][user] = 0
            if server in self.rejects:
                for user in self.rejects[server]:
                    self.rejects[server][user] = 0

            newDbSharesTotal = 0
            newDbRejectsTotal = 0
            newExpPayoutTotal = 0.0

            if requiredSharesTotal == 0:
                logging.debug('Setting expected payout for ' + str(server) + ' to 0')
                sql = 'UPDATE ' + str(server) + ' SET shares = 0'
                self.curs.execute(sql)
                sql = 'UPDATE ' + str(server) + ' SET rejects = 0'
                self.curs.execute(sql)
            else:
                logging.debug('Starting to increase/decrease existing payouts for all users')

                dbSharesTotal = 0
                sql = 'select shares from ' + str(server)
                self.curs.execute(sql)

                for shares in self.curs.fetchall():
                    if shares[0] > 0:
                        dbSharesTotal += shares[0]

                if dbSharesTotal > 0:
                    newPayoutPercent = requiredSharesTotal / float(dbSharesTotal)
                else:
                    # When there are no users in the server table then we find out
                    # global users and use them them to seed a new table.
                    #
                    # Global user shares get used because then we can do percentual
                    # increase/decrease. This way globally well performing users get
                    # more shares when compared to badly performing users

                    users = self.get_users()
                    dbRowCount = 0

                    logging.debug('Making new user table for ' + str(server))

                    sql = 'DELETE FROM ' + str(server)
                    self.curs.execute(sql)
                    #self.database.commit()

                    for user in users:
                        sql = self.sql_insert(server, shares=users[user]['shares'], rejects=0, user=user)
                        self.curs.execute(sql)
                        dbSharesTotal += users[user]['shares']
                        dbRowCount += 1

                    if dbRowCount > 0:
                        self.database.commit()
                        if dbSharesTotal > 0:
                            newPayoutPercent = requiredSharesTotal / float(dbSharesTotal)
                        else:
                            newPayoutPercent = requiredSharesTotal / float(dbRowCount)
                        logging.debug('DB: New user table for ' + str(server) + ' generated')
                    else:
                        # If no users exist at all then return because
                        # changing expected payout is not possible
                        self._lock_release()
                        return -1, -1

                logging.debug('New total payout\'s percent: ' + str(newPayoutPercent))

                sql = 'select user, shares, rejects, diff from ' + str(server)
                self.curs.execute(sql)

                # Build sharesDict and rejectsDict
                # that contain new float share values
                # generated by multiplying each user shares
                # with percentage.

                sharesDict = {}
                rejectsDict = {}
                newSharesTotal = 0
                singleShareValuesTotal = 0.0

                for user, shares, rejects, diff in self.curs.fetchall():
                    if dbSharesTotal > 0:
                        firstShareTypeSelected = True
                        for selectedSharesCount in [shares, rejects]:
                            if selectedSharesCount > 0:
                                floatingShare = float(selectedSharesCount * newPayoutPercent)

                                if firstShareTypeSelected:
                                    selectedDict = sharesDict
                                else:
                                    selectedDict = rejectsDict

                                if floatingShare not in selectedDict:
                                    selectedDict[floatingShare] = {'user': [user], 'diff': [diff]}
                                else:
                                    selectedDict = self.expected_payout_dict_expander(selectedDict, floatingShare, user, diff)

                                if firstShareTypeSelected:
                                    newSharesTotal += int(floatingShare)
                                    newExpPayoutTotal += int(floatingShare) / float(diff) * 50
                                    singleShareValuesTotal += 1 / float(diff) * 50
                                    firstShareTypeSelected = False
                    else:
                        if newPayoutPercent not in sharesDict:
                            sharesDict[newPayoutPercent] = {'user': [user], 'diff': [diff]}
                        else:
                            sharesDict = self.expected_payout_dict_expander(sharesDict, newPayoutPercent, user, diff)
                        newSharesTotal += int(newPayoutPercent)
                        newExpPayoutTotal += int(newPayoutPercent) / float(diff) * 50
                        singleShareValuesTotal += 1 / float(diff) * 50

                payoutDifference = expectedPayout - newExpPayoutTotal
                logging.debug('Initial payout difference caused by percentage multiplication: ' + str(payoutDifference))

                if payoutDifference > 0:
                    addShares = True # Add shares to make expected payout as close as possible
                    logging.debug('  Payout difference is positive, going to add some shares')
                else:
                    addShares = False # Subtract shares to make expected payout as close as possible
                    payoutDifference = payoutDifference * -1
                    logging.debug('  Payout difference is negative, going to subtract some shares')

                # This measures if one loop through all the shares
                # in sharesDict with +1 share addition can cover the payout difference.
                # If this is not possible then instead of adding +1 shares
                # enough shares will be added using loopsRequired to cover the difference

                if (payoutDifference / singleShareValuesTotal) > 1:
                    loopsRequired = int(payoutDifference / singleShareValuesTotal + 1)
                else:
                    loopsRequired = 1
                logging.debug('  Loops to cover difference: ' + str(loopsRequired))

                # This sorts all shares by numbers after decimal point to find out
                # which users should get accumulated leftover shares first. Should be
                # more fair this way since users closest to next integer get leftover
                # shares first.
                # sharesDict/rejectsDict template:
                # sharesDict = { 9.0313: {'user': [user], 'diff': [diff]} }
                # or
                # sharesDict = { 9.0313: {'user': [user1, user2, user3], 'diff': [diff1, diff2, diff3]}

                if addShares:
                    for shares in sorted(sharesDict, key = lambda share: str(share).split('.')[1], reverse = True):
                        (payoutDifference, newExpPayoutTotal, newDbSharesTotal) = self.expected_payout_share_modifier(payoutDifference, sharesDict, shares, loopsRequired, newExpPayoutTotal, newDbSharesTotal, server, addShares)
                else:
                    for shares in sorted(sharesDict, reverse = True):
                        (payoutDifference, newExpPayoutTotal, newDbSharesTotal) = self.expected_payout_share_modifier(payoutDifference, sharesDict, shares, loopsRequired, newExpPayoutTotal, newDbSharesTotal, server, addShares)

                for rejects in rejectsDict:
                    newDbRejectsTotal += self.expected_payout_sql_updater(server, rejectsDict, rejects, rejectsMode=True)

            logging.debug('DB: Commiting changes to the database')
            self.database.commit()
            self._lock_release()
            return newDbSharesTotal, newDbRejectsTotal, newExpPayoutTotal
        except Exception, e:
            logging.info('Exception caught in bitHopper.database.change_expected_payout: ' + str(e))
        finally:
            self._lock_release()

    def get_expected_payout(self, server):
        self._lock_get('expected_payout')
        sql = 'select shares, diff, rejects from ' + str(server)
        self.curs.execute(sql)
        result = self.curs.fetchall()
        expected = 0
        for item in result:
            shares = item[0] - item[2]
            difficulty = item[1]
            expected += float(shares)/difficulty * 50
            
        self._lock_release()
        return expected

    def update_rejects(self, server, shares, user, password):
        self._lock_get('update_rejects')
        if server not in self.rejects:
            self.rejects[server] = {}
        if user not in self.rejects[server]:
            self.rejects[server][user] = 0
        self.rejects[server][user] += shares
        self._lock_release()

    def make_table(self, server_name):
        while not self.curs:
            time.sleep(0.1)
        sql = "CREATE TABLE IF NOT EXISTS "+server_name +" (diff REAL, shares INTEGER, rejects INTEGER, stored_payout REAL, user TEXT)"
        self.curs.execute(sql)


    def get_rejects(self, server):
        self._lock_get('get_rejects')
        self.make_table(server)

        sql = 'select rejects from ' + str(server)
        self.curs.execute(sql)
        shares = 0
        for info in self.curs.fetchall():
            shares += int(info[0])
        self._lock_release()
        return shares

    def set_payout(self, server, payout):
        self._lock_get('set_payout')
        if server not in self.payout:
            self.payout[server] = None
        self.payout[server] = payout
        return self._lock_release()

    def get_payout(self, server):
        self._lock_get('get_payout')
        sql = 'select stored_payout from ' + server + ' where diff=1'
        self.curs.execute(sql)
        payout = 0
        for info in self.curs.fetchall():
            payout += float(info[0])
        self._lock_release()
        return payout

