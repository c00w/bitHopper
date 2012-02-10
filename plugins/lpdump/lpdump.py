#!/usr/bin/python
#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

import random, re, sys
import time, threading, socket

from peak.util import plugins
# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class LpDump():
    def __init__(self, bitHopper):
        """
        Hook the lp module to print out blocks to a file
        """
        self.bitHopper = bitHopper
        self.file_name = self.bitHopper.config.get('plugins.lpdump', 'file', None)
        if not self.file_name:
            return

        hook_ann = plugins.Hook('plugins.lp.add_block.start')
        hook_ann.register(self.on_block)

    def on_block(self, LP, block, work, server):
        """
        Recieves the current block and server and dumps it to file
        """
        fd = None
        try:
            # determine if application is a script file or frozen exe
            if hasattr(sys, 'frozen'):
                application_path = os.path.dirname(sys.executable)
            elif __file__:
                application_path = os.path.dirname(__file__)
            fd = open(os.path.join(application_path, self.file_name), 'brwa+')
        except:
            fd = open(self.file_name, 'brwa+')

        fd.write(time.strftime('%H%M%S') + ":" + block + ":" + server + "\n" )
        fd.close()

        
