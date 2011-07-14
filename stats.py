#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import diff
import pool

def stats_dump(server, stats_file):
    if stats_file != None:
        stats_file.write(pool.get_current()['name'] + " " + str(pool.get_current()['user_shares']) + " " + str(diff.difficulty) + "\n")
