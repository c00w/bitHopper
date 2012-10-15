"""
Deals with lagging logic for the system
"""

import btcnet_info
import gevent

lagged = set() #A list of tuples (server, worker, password)
    
def lag( server, worker, password):
    """Mark an item as lagged """
    if (server, worker, password) not in lagged:
        lagged.add((server, worker, password))
    
def filter_lag( source):
    """
    Lag based filter
    """
    for server, worker, password in source:
        if (server, worker, password) not in lagged:
            yield (server, worker, password)
    
