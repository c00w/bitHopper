"""
File implementing the actuall logic for the business side
"""

import btcnet_info
from .. import Workers
from . import LaggingLogic, _select
import logging, traceback, gevent
    
i = 1
Servers = set()
gevent.spawn(generate_servers)
gevent.sleep(0)
    
def difficulty_cutoff(source):
    """
    returns the difficulty cut off for the pool
    """
    
    diff = btcnet_info.get_difficulty(source.coin)
    if not diff:
        while not diff:
            gevent.sleep(0)
            diff = btcnet_info.get_difficulty(source.coin)
            
    diff = float(diff)
    
    #Propositional Hopping
    if source.payout_scheme in ['prop']:
        return diff * 0.435
        
    #Score Hopping
    if source.payout_scheme in ['score']:
        # Incorrect method. Just using it for now.
        # TODO FIX IT TO USE MINE_C CONSTANTS 
        return diff * 0.435
    
def valid_scheme( source):
    """
    This is a generator that produces servers where the shares are hoppable or the method is secure(SMPPS etc...)
    """
    for site in source:
    
        #Check if we have a payout scheme
        scheme = site.payout_scheme
        if not scheme:
            continue
            
        #Check if this is a secure payout scheme
        if scheme.lower() in ['pps', 'smpps', 'pplns']:
            yield source
        
        if scheme.lower() in ['prop', 'score']:
        
            #Check if we have a share count
            shares = float(site.shares)
            if not shares:
                continue
                
            shares = float(shares)
            if shares < difficulty_cutoff(site):
                yield source
                
def valid_credentials( source):
    """
    Only allows through sites with valid credentials
    """
    for site in source:
    
        #Pull Name
        name = site.name
        if not name:
            continue
            
        workers = Workers.get_worker_from(name)
        if not workers:
            continue
            
        for user, password in workers:
            if len(list(LaggingLogic.filter_lag([(name, user, password)]))):
                yield site
        
        
def filter_hoppable( source):
    """
    returns an iterator of hoppable pools
    """
    
    for pool in source:
        if not pool.payout_scheme:
            continue
        if pool.payout_scheme.lower() in ['prop','score']:
            yield pool
            
def filter_secure( source):
    """
    Returns an iterator of secure pools
    """
    
    for pool in source:
        if not pool.payout_scheme:
            continue
        if pool.payout_scheme.lower() in ['pplns', 'smpps', 'pps']:
            yield pool
        
def filter_best( source):
    """
    returns the best pool or pools we have
    """
    pools = [x for x in source]
    
    #See if we have a score or a prop pool
    hoppable = list(filter_hoppable( pools))
    
    if hoppable:
        pool_ratio = lambda pool: float(pool.shares) / difficulty_cutoff(pool)
        min_ratio = min( map(pool_ratio, hoppable))
        for pool in hoppable:
            if pool_ratio(pool) == min_ratio:
                return set(pool)    
    
    #Select a backup pool
    backup = list(filter_secure(pools))
    if backup:
        return set(backup)
        
    raise ValueError("No valid pools configured")
    
def generate_servers():
    """
    Method that generate the best server
    """
    while True:
        try:
            global Servers
            Servers = list(filter_best(
                            valid_scheme(
                             valid_credentials(
                              btcnet_info.get_pools()))))
        except Exception as error:
            logging.error(traceback.format_exc())
        gevent.sleep(30)
    
def get_server():
    """
    Returns an iterator of valid servers
    """
    return _select(Servers)
        

