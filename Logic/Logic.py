"""
File implementing the actuall logic for the business side
"""

from btcnet_wrapper import btcnet_info
import Workers

class Logic():
    """
    Logic wrapper class
    """
    
    def __init__(self):
        self.i = 1
        
    def self.difficulty_cutoff(self, source):
        diff = btcnet_info.get_coins(
        
    def valid_scheme(self, source):
        """
        This is a generator that produces servers where the shares are hoppable or the method is secure(SMPPS etc...)
        """
        for site in source:
        
            #Check if we have a payout scheme
            scheme = source.payout_scheme
            if not source:
                continue
                
            #Check if this is a secure payout scheme
            if source.payout_scheme.lower() in ['pps', 'smpps', 'pplns']
                yield source
            
            if source.payout_scheme.lower() in ['prop']:
            
                #Check if we have a share count
                shares = source.shares
                if not shares:
                    continue
                    
                shares = float(shares)
                if shares < self.difficulty_cutoff(source):
                    yield source
                    
    def valid_credentials(self, source):
        """
        Only allows through sites with valid credentials
        """
        for site in source
        
            #Pull Name
            name = site.name
            if not name:
                continue
                
            workers = Workers.get_worker_from(name)
            if not workers:
                continue
            
            yield site
            
    def filter_hoppable(self, source):
        """
        returns an iterator of hoppable pools
        """
        
        for pool in source:
            if not pool.payout_scheme:
                continue
            if pool.payout_scheme.lower() in ['prop','score']:
                yield pool
                
    def filter_secure(self, source):
        """
        Returns an iterator of secure pools
        """
        
        for pool in source:
            if not pool.payout_scheme:
                continue
            if pool.payout_scheme.lower() in ['pplns', 'smpps', 'pps']:
                yield pool
            
    def find_best(source):
        pools = [x for x in source]
        
        #See if we have a score or a prop pool
        hoppable = list(self.filter_hoppable(self, pools))
        
        if hoppable:
            min_ratio = min(float(pool.shares) / self.difficulty_cutoff(pool) for pool in hoppable)
            for pool in hoppable:
                if float(pool.shares) / self.difficulty_cutoff(pool) = min_ratio:
                    return pool    
        
        #Select a backup pool
        backup = list(self.filter_secure(pools))
        if backup:
            return self.select(backup)
            
        raise ValueError("No valid pools configured")
        
    def get_server(self):
        servers = self.valid_scheme(self.valid_credentials(btcnet_info.get_pools()))
        server = self.find_best(servers)
        return server
