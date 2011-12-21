#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import random, re, logging
import re
import eventlet
from eventlet.green import time, threading, socket
import eventlet.patcher
irclib = eventlet.patcher.import_patched('irclib')
SimpleIRCClient = irclib.SimpleIRCClient

from peak.util import plugins

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class LpBot(SimpleIRCClient):
    def __init__(self, bitHopper):
        SimpleIRCClient.__init__(self)
        self.bitHopper = bitHopper
        self.nick = 'lp' + str(random.randint(1,9999999999))
        self.chan_list=[]
        self.newblock_re = re.compile('\*\*\* New Block \{(?P<server>.+)\} - (?P<hash>.*)')
        self.hashes = ['']
        self.hashinfo = {'':''}
        self.server=''
        self.current_block=''
        hook_startup = plugins.Hook('plugins.lpbot.init')
        hook_startup.notify(self)
        hook_ann = plugins.Hook('plugins.lp.announce')
        hook_ann.register(self.announce)

        eventlet.spawn_n(self.run)
        eventlet.spawn_n(self.process_forever)
        self.lock = threading.RLock()

    def process_forever(self):
        while True:
            self.ircobj.process_once(0.2)
            eventlet.sleep(0.2)
            
    def run(self):
        while True:
                if self.is_connected():
                        self.join()
                else:
                        self.chan_list = []
                        self._connect()
                        print "Connect returned"
                eventlet.sleep(self.bitHopper.config.getint('lpbot', 'run_interval'))
    
    def _connect(self):
        logging.info( "Connecting...")
        try:
            irc_server = self.bitHopper.config.get('lpbot', 'irc_server')
            irc_port = self.bitHopper.config.getint('lpbot', 'irc_port')
            self.connect(irc_server, irc_port, self.nick)
        except Exception, e:
            logging.info( e)

    def is_connected(self):
        return self.connection.is_connected();

    def on_disconnect(self, c, e):
        logging.info( "Disconnected...")
        self.chan_list=[]
        hook = plugins.Hook('plugins.lpbot.on_disconnect')
        hook.notify(self,c ,e)
        self.connection.execute_delayed(10, self._connect)

    def on_connect(self, c, e):
        self.join()
        hook = plugins.Hook('plugins.lpbot.on_connect')
        hook.notify(self,c ,e)

    def on_pubmsg(self, c, e):
        with self.lock:
            hook = plugins.Hook('plugins.lpbot.on_pubmsg')
            hook.notify(self,c ,e)
            bl_match = self.newblock_re.match(e.arguments()[0])
            if bl_match != None:
                last_hash = bl_match.group('hash')
                server = bl_match.group('server')
                self.decider(server, last_hash)

    def get_last_block(self):
        return self.hashes[-1]

    def decider(self, server, block):
        with self.lock:
            last_server = self.server
            last_block = self.get_last_block()
            votes = 0
            total_votes = 0

            if block not in self.hashes:
                ### New block I know nothing about
                logging.info( "New Block: {" + str(server) + "} - " + block)
                self.hashes.append(block)
                if len(self.hashes) > 50:
                    del self.hashes[0];
                self.hashinfo[block] = [server]
                # Am I working on this now?
                if self.current_block == block:
                    logging.info( "Server selected: " + server)
                    self.server = server
                    votes = 1
                    total_votes = 1
                else:
                    # Info added, I have nothing else to do
                    #logging.info( "Unknown work - " + block)
                    return
            else:
                # Add a vote
                self.hashinfo[block].append(server)
                # Talley the votes based on who we have selected so far
                for v in self.hashinfo[block]:
                    if v == self.server:
                        votes += 1
                    total_votes += 1
                
                # If I haven't received the new work yet, I don't want to decide anything, just store it
                if self.current_block != block:
                    #logging.info( "Old  work - " + block
                    return

                logging.info( "Total Votes: " + str(total_votes))
                # Enough votes for a quarum?
                if total_votes > self.bitHopper.config.getint('lpbot','min_votes'):
                    # Enought compelling evidence to switch?
                    # Loop through unique servers for the block
                    for test_server in set(self.hashinfo[block]):
                        test_votes = 0
                        test_total_votes = 0
                        logging.info( "Tallying votes for " + test_server)
                        ## Talley up the votes for that server
                        for test_vote in self.hashinfo[block]:
                            test_total_votes += 1
                            if test_vote == test_server:
                                test_votes += 1
                        logging.info( str(test_votes) + " out of " + str(test_total_votes) + " votes.")
                        if float(test_votes) / test_total_votes > self.bitHopper.config.getfloat('lpbot','vote_threshold'):
                            if self.server != test_server:
                                hook = plugins.Hook('plugins.lpbot.decider.minority')
                                hook.notify(self, server, block, test_server, test_votes, test_total_votes)
                                logging.info( "In the minority, updating to  " + test_server + ": " + str(test_votes) + "/" + str(test_total_votes))
                                self.server = test_server
                                votes = test_votes
                                total_votes = test_total_votes
                            else:
                                hook = plugins.Hook('plugins.lpbot.decider.majority')
                                hook.notify(self, server, block, test_server, test_votes, test_total_votes)
                                logging.info( "In the majority, keeping server")
                        else:
                            logging.info( "Not enough votes in one direction to make a decision")
                else: # Not enough for quarum, select first
                    self.server = self.hashinfo[block][0]
                    votes = 0
                    total_votes = 0
                    for vote_server in self.hashinfo[block]:
                        if vote_server == self.server:
                            votes += 1
                        total_votes += 1
            
            if self.server != last_server:
                hook = plugins.Hook('plugins.lpbot.decider.best_guess')
                hook.notify(self, self.server, votes, total_votes, self.current_block)
                self.say("Best Guess: {" + self.server + "} with " + str(votes) + " of " + str(total_votes) + " votes - " + self.current_block)
                self.bitHopper.lp.set_owner(self.server, self.current_block)

            # Cleanup
            # Delete any orbaned blocks out of blockinfo
            logging.info( "Clean Up...")
            for clean_block, clean_val in self.hashinfo.items():
                if clean_block not in self.hashes:
                    logging.info( "Deleting old work... " + clean_block)
                    del self.hashinfo[clean_block]

    def say(self, text):
        hook = plugins.Hook('plugins.lpbot.say')
        hook.notify(self, text)
        self.connection.privmsg("#bithopper-lp", text)            
        
    def announce(self, lp, body, server, last_hash):
        with self.lock:
            hook = plugins.Hook('plugins.lpbot.announce')
            hook.notify(self, server, last_hash)
            try:
                if self.is_connected():
                    self.server=''
                    self.current_block = last_hash
                    logging.info( "Announcing: *** New Block {" + str(server) + "} - " + last_hash)
                    self.say("*** New Block {" + str(server) + "} - " + last_hash)
                    self.decider(server, last_hash)
                else:
                    logging.info( "Not connected to IRC...")
            except Exception, e:
                logging.info( "********************************")
                logging.info( "*****  ERROR IN ANNOUCE  *******")
                logging.info( "********************************")
                logging.info( str(e))

    def join(self):
        hook = plugins.Hook('plugins.lpbot.join')
        hook.notify(self)
        if '#bithopper-lp' not in self.chan_list:
            self.connection.join('#bithopper-lp')
            self.chan_list.append('#bithopper-lp')

#class test_eventargs():
#    def __init__(self, message):
#        self.arguments = [message]

#if __name__ == "__main__":
#    bot = LpBot()
#    while not bot.is_connected:
#        thread.sleep(3)
#    
#    print 'Testing me first, everyone agrees'
#    bot.announce('test', '1')
#    bot.on_pubmsg('', test_eventargs('*** New Block {test} - 1'))
#    bot.on_pubmsg('', test_eventargs('*** New Block (test) - 1'))
#    bot.on_pubmsg('', test_eventargs('*** New Block (test) - 1'))
#    bot.on_pubmsg('', test_eventargs('*** New Block (test) - 1'))
#    bot.on_pubmsg('', test_eventargs('*** New Block (test) - 1'))
#
#    print 'Testing someone first, me later with wrong server'


