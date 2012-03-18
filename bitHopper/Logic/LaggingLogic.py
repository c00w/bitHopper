"""
Deals with lagging logic for the system
"""

import gevent
from .. import Network

lagged = set() #A list of tuples (server, worker, password)
    
def lag( server, worker, password):
    if (server, worker, password) not in lagged:
        lagged.add((server, worker, password))
        gevent.spawn(_unlag, server, worker, password)
    
def _unlag( server, worker, password):
    n = 1
    while True:
        work = Network.get_work_credentials(server, worker, password)
        if worker:
            lagged.remove((server, worker, password))
            return
        gevent.sleep(60 * n)
        n = n+1 if n < 10 else 10
        
def filter_lag( source):
    for server, worker, password in source:
        if (server, worker, password) not in lagged:
            yield (server, worker, password)
    
