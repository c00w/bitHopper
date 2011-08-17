#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import urllib2
import re
from twisted.internet.task import LoopingCall

class Difficulty():
    "Stores difficulties and automaticlaly updates them"
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.difficulty = 1690906.2047244
        self.nmc_difficulty = 94037.96
        self.ixc_difficulty = 16384
        self.i0c_difficulty = 1
        call = LoopingCall(self.update_difficulty)
        call.start(60*60*6)

    def get_difficulty(self):
        return self.difficulty
    
    def get_nmc_difficulty(self):
        return self.nmc_difficulty

    def get_ixc_difficulty(self):
        return self.ixc_difficulty
    
    def get_i0c_difficulty(self):
        return self.i0c_difficulty

    def update_difficulty(self):
        "Tries to update difficulty from the internet"
        self.bitHopper.log_msg('Updating Difficulty')
        try:
            req = urllib2.Request('http://blockexplorer.com/q/getdifficulty')
            response = urllib2.urlopen(req)
            diff_string = response.read()
            self.difficulty = float(diff_string)
            self.bitHopper.log_msg(str(diff_string))
        except:
            pass
        
        self.bitHopper.log_msg('Updating NameCoin Difficulty')
        try:
            req = urllib2.Request('http://namebit.org/')
            response = urllib2.urlopen(req)
            diff_str = response.read()
            output = re.search('<td id="difficulty">([.0-9]+)</td>', diff_str)
            output = output.group(1)
            self.nmc_difficulty = float(output)
            self.bitHopper.log_msg(str(self.nmc_difficulty))
        except:
            pass
