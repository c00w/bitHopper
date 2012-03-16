"""
Pulls everything togethor to generate a list of server, user, password
tuples that can be mined at
"""
from .. import Workers
from . import SLogic

class Logic():
    
    def __init__(self):
        self.i = 0
        
    def generate_tuples(self, server):
        tokens = Workers.get_worker_from(server)
        for user, password in tokens:
            yield (server, user, password)
        
    def get_server(self):
        return self._select(list(self.generate_tuples(SLogic.get_server())))
        
    def _select(self, item):
        self.i = self.i + 1 if self.i < 10**10 else 0
        return item[self.i % len(item)]
        
