"""
File implementing the actuall logic for the business side
"""
try:
    from btcnet_wrapper import btcnet_info
except ImportError:
    import btcnet_info
import gevent

class Logic():
    """
    Logic wrapper class
    """
    
    def __init__(self, Workers):
        self.i = 1
        self._server = set()
        gevent.spawn(self.generate_servers)
        gevent.sleep(0)
        self.Workers = Workers
        
    def difficulty_cutoff(self, source):
        """
        returns the difficulty cut off for the pool
        """
        diff = btcnet_info.get_difficulty(source.coin)
        diff = float(diff)
        
        #Propositional Hopping
        if source.payout_scheme in ['prop']:
            return float(diff) * 0.435
            
        #Score Hopping
        if source.payout_scheme in ['score']:
            # Incorrect method. Just using it for now.
            # TODO FIX IT TO USE MINE_C CONSTANTS 
            return float(diff) * 0.435
        
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
            if source.payout_scheme.lower() in ['pps', 'smpps', 'pplns']:
                yield source
            
            if source.payout_scheme.lower() in ['prop', 'score']:
            
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
        for site in source:
        
            #Pull Name
            name = site.name
            if not name:
                continue
                
            workers = self.Workers.get_worker_from(name)
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
            
    def filter_best(source):
        """
        returns the best pool or pools we have
        """
        pools = [x for x in source]
        
        #See if we have a score or a prop pool
        hoppable = list(self.filter_hoppable(self, pools))
        
        if hoppable:
            min_ratio = min(float(pool.shares) / self.difficulty_cutoff(pool) for pool in hoppable)
            for pool in hoppable:
                if float(pool.shares) / self.difficulty_cutoff(pool) == min_ratio:
                    return set(pool)    
        
        #Select a backup pool
        backup = list(self.filter_secure(pools))
        if backup:
            return set(backup)
            
        raise ValueError("No valid pools configured")
        
    def generate_servers(self):
        """
        Method that generate the best server
        """
        while True:
            self._servers = list(self.filter_best(self.valid_scheme(self.valid_credentials(btcnet_info.get_pools()))))
            gevent.sleep(30)
            
        
    def _select(pools):
        return pools[self.i % len(pools)]
        
    def get_server(self):
        return self._select(self._servers)
        

