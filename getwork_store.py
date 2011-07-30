import time

class Getwork_store:
    
    def __init__(self, bithopper):
        self.data = {}
        self.bitHopper = bithopper
    
    def add(self, server, merkle_root):
        self.data[merkle_root] = {'name':server["name"], 'timestamp':time.time()}
        return
    
    def get_server(self, merkle_root):
        if self.data.has_key(merkle_root):
            return self.data[merkle_root]['name']
        self.bitHopper.log_msg('Work not found in store')
        return None
    
    def prune(self):
        for key, work in self.data.items():
            if work['timestamp'] < (time.time() - (60*5)):
                del self.data[key]
        return
