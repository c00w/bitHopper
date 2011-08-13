from irclib import SimpleIRCClient
import time
import random
import re
import thread
import urllib2

class LpBot(SimpleIRCClient):
	def __init__(self):
		SimpleIRCClient.__init__(self)
		self.nick = 'lp' + str(random.randint(1,9999999999))
		self.connection.add_global_handler('disconnect', self._on_disconnect, -10)
		self.chan_list=[]
		self.notice_re = re.compile('[\d+/\d+ \d+:\d+] \*\*\* New block found by \{(?P<server>.+)\} Block Number: \((?P<block_number>\d+)\).*')
		self.newblock_re = re.compile('\*\*\* New Block: (?P<block_number>\d+)')
		self.first_block = 0
		self.last_block = 0
		self.initialized = False;
		# TODO: Use twisted
		thread.start_new_thread(self.run,())
		thread.start_new_thread(self.update_last_block,())
		thread.start_new_thread(self.ircobj.process_forever,())

	def run(self):
	        while(True):
        	        if self.is_connected():
                	        self.join()
                	else:
                       		print "Connecting..."
                        	self._connect()
                	time.sleep(1)
	
	def _connect(self):
		self.connect('chat.freenode.net', 6667, self.nick)

	def is_connected(self):
		return self.connection.is_connected();

	def _on_disconnect(self, c, e):
		self.chan_list=[]
		self.connection.execute_delayed(30, self._connect)

	def on_pubmsg(self, c, e):
		bl_match = self.newblock_re.match(e.arguments()[0])
		if bl_match != None:
			block = bl_match.group('block_number')
			if self.first_block == 0:
				self.first_block = block
			if block > self.last_block:
				self.last_block = block
		
		match = self.notice_re.match(e.arguments()[0])
		if match != None:
			print "Server: " + match.group('server')
			print "Block Number: " + match.group('block_number')
			
		
	def announce(self, server):
		try:
			#self.do_update_last_block()
			print "Identified as : " 
			print str(server)
			if self.initialized:
				self.connection.privmsg("#bithopper-lp", "*** New block found by {" + str(server) + "} Block Number: (" + str(self.last_block) + ")")
		except Exception, e:
			print "***************************************"
			print "*****  ERROR IN ANNOUCE         *******"
			print "***************************************"
			print e.value

	def join(self):
		if '#bithopper-lp' not in self.chan_list:
	                self.connection.join('#bithopper-lp')
			self.chan_list.append('#bithopper-lp')
		self.ircobj.process_forever()

	def update_last_block(self):
		while(True):
			self.do_update_last_block()
			# TODO: Use twisted
			time.sleep(5)

	def do_update_last_block(self):
		try:
	                handle = urllib2.urlopen('http://blockexplorer.com/q/getblockcount')
        	        if handle != None:
                		block_num = int(handle.read())
                        	handle.close()
				if self.initialized:
					if block_num > self.last_block:
						print "New Block: " + str(self.last_block)
						self.connection.privmsg("#bithopper-lp", "*** New Block: " + str(block_num))
				else:
                                        if self.first_block == 0:
                                            self.first_block = block_num
                                        elif self.first_block != block_num:
                                            self.initialized=True
                                        
				self.last_block = block_num
		except Exception, e:
                	print e.value
