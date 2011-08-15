from irclib import SimpleIRCClient
import time
import random
import re
import thread
import urllib2

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
		# TODO: Use twisted
		thread.start_new_thread(self.run, ())
		thread.start_new_thread(self.ircobj.process_forever,())

	def run(self):
	        while(True):
        	        if self.is_connected():
                	        self.join()
                	else:
				self.chan_list = []
                        	self._connect()
				print "Connect returned"
                	time.sleep(15)
	
	def _connect(self):
		print "Connecting..."
		try:
			self.connect('chat.freenode.net', 6667, self.nick)
		except Exception, e:
			print e

	def is_connected(self):
		return self.connection.is_connected();

	def on_disconnect(self, c, e):
		print "Disconnected..."
		self.chan_list=[]
		self.connection.execute_delayed(10, self._connect)

	def on_connect(self, c, e):
		self.join()

	def on_pubmsg(self, c, e):
		bl_match = self.newblock_re.match(e.arguments()[0])
		if bl_match != None:
			last_hash = bl_match.group('hash')
			server = bl_match.group('server')
			self.decider(server, last_hash)

	def get_last_block(self):
		return self.hashes[-1]

	def decider(self, server, block):
		last_server = self.server
		last_block = self.get_last_block()
		votes = 0
		total_votes = 0

		if block not in self.hashes:
			### New block I know nothing about
			print "New Block: {" + str(server) + "} - " + block
			self.hashes.append(block)
			if len(self.hashes) > 50:
				del self.hashes[0];
			self.hashinfo[block] = [server]
			# Am I working on this now?
			if self.current_block == block:
				print "Server selected: " + server
				self.server = server
				votes = 1
				total_votes = 1
			else:
				# Info added, I have nothing else to do
				print "Unknown work - " + block
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
				print "Old  work - " + block
				return

			print "Total Votes: " + str(total_votes)
			# Enough votes for a quarum?
			if total_votes > 5:
				# Enought compelling evidence to switch?
				# Loop through unique servers for the block
				for test_server in set(self.hashinfo[block]):
					test_votes = 0
					test_total_votes = 0
					print "Tallying votes for " + test_server
					## Talley up the votes for that server
					for test_vote in self.hashinfo[block]:
						test_total_votes += 1
						if test_vote == test_server:
							test_votes += 1
					print str(test_votes) + " out of " + str(test_total_votes) + " votes."
					if float(test_votes) / test_total_votes > .5 and self.server != test_server:
						print "In the minority, updating to  " + test_server + ": " + str(test_votes) + "/" + str(test_total_votes)
						self.server = test_server
						votes = test_votes
						total_votes = test_total_votes
			else: # Not enough for quarum, select first
				self.server = self.hashinfo[block][0]
				votes = 0
				total_votes = 0
				for vote_server in self.hashinfo[block]:
					if vote_server == self.server:
						votes += 1
					total_votes += 1
		
		if self.server != last_server:
			self.say("Best Guess: {" + self.server + "} with " + str(votes) + " of " + str(total_votes) + " votes - " + self.current_block)
			self.bitHopper.lp.lp_api(self.server, self.current_block)

		# Cleanup
		# Delete any orbaned blocks out of blockinfo
		print "Clean Up..."
		for clean_block, clean_val in self.hashinfo.items():
			if clean_block not in self.hashes:
				print "Deleting old work... " + clean_block
				del self.hashinfo[clean_block]

	def say(self, text):
		self.connection.privmsg("#bithopper-lp", text)			
		
	def announce(self, server, last_hash):
		try:
			if self.is_connected():
				self.server=''
				self.current_block = last_hash
				print "Announcing: *** New Block {" + str(server) + "} - " + last_hash
				self.say("*** New Block {" + str(server) + "} - " + last_hash)
				self.decider(server, last_hash)
			else:
				print "Not connected to IRC..."
				self.bitHopper.lp.lp_api(self.server, self.current_block)
		except Exception, e:
			print "********************************"
			print "*****  ERROR IN ANNOUCE  *******"
			print "********************************"
			print e

	def join(self):
		if '#bithopper-lp' not in self.chan_list:
	                self.connection.join('#bithopper-lp')
			self.chan_list.append('#bithopper-lp')

#class test_eventargs():
#	def __init__(self, message):
#		self.arguments = [message]

#if __name__ == "__main__":
#	bot = LpBot()
#	while not bot.is_connected:
#		thread.sleep(3)
#	
#	print 'Testing me first, everyone agrees'
#	bot.announce('test', '1')
#	bot.on_pubmsg('', test_eventargs('*** New Block {test} - 1'))
#	bot.on_pubmsg('', test_eventargs('*** New Block (test) - 1'))
#	bot.on_pubmsg('', test_eventargs('*** New Block (test) - 1'))
#	bot.on_pubmsg('', test_eventargs('*** New Block (test) - 1'))
#	bot.on_pubmsg('', test_eventargs('*** New Block (test) - 1'))
#
#	print 'Testing someone first, me later with wrong server'


