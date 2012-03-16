import gevent
from .. import Network

class Logic():
    """
    Deals with lagging logic for the system
    """
    
    def __init__(self):
        self.lagged = set() #A list of tuples (server, worker, password)
        
    def lag(self, server, worker, password):
        if (server, worker, password) not in self.lagged:
            self.lagged.add((server, worker, password))
            gevent.spawn(self.unlag, server, worker, password)
        
    def _unlag(self, server, worker, password):
        n = 1
        while True:
            work = Network.get_work_credentials(server, worker, password)
            if worker:
                self.lagged.remove((server, worker, password))
                return
            gevent.sleep(60 * n)
            n = n+1 if n < 10 else 10
            
    def filter_lag(self, source):
        for server, worker, password in source:
            if (server, worker, password) not in self.lagged:
                yield (server, worker, password)
    
