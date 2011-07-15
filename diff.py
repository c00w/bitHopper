#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import urllib2

def get_difficulty():
    try:
        req = urllib2.Request('http://blockexplorer.com/q/getdifficulty')
        response = urllib2.urlopen(req)
        diff_string = response.read()
        return float(diff_string)
    except:
        return 1563027.99611622
difficulty = get_difficulty()
