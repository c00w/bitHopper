# tracks accuracy of block predictions as noted in lp.blocks['_owner']
# required pident plugin to work
import time
import eventlet
import traceback

from eventlet.green import time, threading
from peak.util import plugins

class BlockAccuracy:
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.announce_threshold = 20
        self.log_dbg('Registering hooks')
        self.blocks = {}
        # register plugin hooks        
        hook = plugins.Hook('plugins.pident.verified')
        hook.register(self.block_verified)
        

    def log_msg(self, msg):
        self.bitHopper.log_msg(msg, cat='block-accuracy')
    
    def log_dbg(self, msg):
        self.bitHopper.log_dbg(msg, cat='block-accuracy')
        
    def log_trace(self, msg):
        self.bitHopper.log_trace(msg, cat='block-accuracy')
        
    def block_verified(self, block, pool):
        if block != None and pool != None:
            self.log_dbg('Adding block owner ' + str(pool) + ' for ' + str(block))
            self.blocks[block] = {}
            self.blocks[block]['pident_verified'] = pool
        else:
            self.log_msg('Bad notify: ' + str(block) + '/' + str(pool))
        pass
    
    def report(self):
        pools = {}
        for pool in self.bitHopper.pools.get_servers():
            pools[pool] = {}
            pools[pool]['hit'] = 0
            pools[pool]['miss'] = 0
            pools[pool]['total'] = 0
        
        # for each block see if we have verification
        try:
            for block in self.bitHopper.lp.blocks:
                lp_owner = self.bitHopper.lp.blocks[block]['_owner']
                pident_owner = None
                if block in self.blocks:
                    pident_owner = self.blocks[block]['pident_verified']
                if lp_owner == pident_owner:
                    pools[lp_owner]['hit'] += 1
                    pools[pool]['total'] += 1
                else:
                    pools[lp_owner]['miss'] += 1
                    pools[pool]['total'] += 1
                    
            for pool in pools:
                total = pools[pool]['total']
                hit = pools[pool]['hit']
                miss = pools[pool]['miss']
                pct = (float(hit) / total) * 100
                msg = '%(pool)s %(hit)d hits / %(miss)d misses / (total)d / %(hit_percent)2.1f%% hit' % \
                      {"pool": pool, "hit":hit, "miss":miss, "total":total, "hit_percent":pct}
                
        except Exception, e:
            if self.bitHopper.options.debug:
                traceback.print_exc()
    
    #def lp_announce(self, lpobj, body, server, block):
    #    self.log_msg(server + ': ' + block)
    #    if block not in self.blocks:
    #        self.blocks[block] = {}
    #        self.blocks[block]['verified'] = None
    #    if 'initial_timestamp' in self.blocks:
    #        now = time.time()
    #        if now - self.blocks['initial_timestamp'] < self.announce_threshold:
    #            # assume same block
    #            self.blocks[block]['initial'] = server
    #        else:
    #            self.log_dbg('Rejected ' + server + ' for ' + block + ' due to time')
    #    else:
    #        # first block seen
    #        self.blocks[block]['initial_timestamp'] = time.time()
    #        self.blocks[block]['initial'] = server
    #        