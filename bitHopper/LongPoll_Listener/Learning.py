import random
import btcnet_info
import gevent
import logging
import json
from collections import defaultdict

import bitHopper.Logic
import bitHopper.Network

try:
    import numpy as np
except ImportError:
    np = None

blocks_timing = {}
blocks_calculated = {}
blocks_actual = {}

#wait for these pools before calculating results
used_pools = ['deepbit']
weights = [-1, 0]

def set_neg(block):
    if block not in blocks_actual:
        blocks_actual[block] = 0

def learn_block(blocks, current_block):
    print 'learn_block called'
    #import block data
    for block in blocks:
        if block not in blocks_timing:
            blocks_timing[block] = blocks[block]
            gevent.spawn_later(60*60*1.5, set_neg, block)

    #update current_block
    if len(blocks[current_block]) < len(blocks_timing[current_block]):
        blocks_timing[current_block] = blocks[current_block]

    #determine if we should do a prediction
    if have_all_data(blocks[current_block]):
        calculate_block(current_block)

def have_all_data(block_info):
    for pool in used_pools:
        if pool not in block_info:
            return False
    return True

def vec_mult(a, b):
    return sum([i*j for i, j in zip(a,b)])

def extract_vector(current_block):
    result = [1]
    for pool in used_pools:
        result.append(blocks_timing[current_block][pool])
    return result

def calculate_block(current_block):
    print 'calculate block called'
    if vec_mult(weights, extract_vector(current_block)) > 0:
        print 'triggered'
        btcnet_info.get_pool('deepbit').namespace.get_node('shares').set_value(0)
        #Reset shares on deepbit
        blocks_calculated[current_block] = 1
    else:
        blocks_calculated[current_block] = 0

def check_learning():
    print 'Check learning started'
    while True:
        gevent.sleep(60)
        deepbit_blocks = set(json.loads(btcnet_info.get_pool('deepbit').blocks))
        for block in blocks_timing:
            if block in blocks_actual and blocks_actual[block] == 1:
                continue
            if block in deepbit_blocks:
                blocks_actual[block] = 1
                print 'Block %s has training value %s' % (block, blocks_actual[block])

#Connect to deepbit if possible    
def poke_deepbit():
    choices = list(bitHopper.Logic.generate_tuples('deepbit'))
    if len(choices) == 0:
        logging.info('No workers for deepbit. Disabling machine learning') 
        return
    server, username, password = random.choice(choices)
    url = btcnet_info.get_pool(server)['mine.address']
    bitHopper.Network.send_work_lp(url, username, password, 'deepbit')

def calc_good_servers():
    used_pools = set()
    used_pools.add('deepbit')

    def yield_timings_block(blocks):
        for block in blocks:
            for server in block:
                yield server
    times_found = list(yield_timings_block(block for name, block in blocks_timing.iteritems()))
    def make_count_map(servers):
        count = defaultdict(int)
        for server in servers:
            count[server] += 1
        return sorted(list(count.iteritems()), key=lambda x: -1 * x[1])

    counts = make_count_map(times_found)
    #Use the top level of info, plus deepbit
    if not counts:
        return used_pools
    cutoff = counts[0][1]
    for server, count in counts:
        if count >= cutoff:
            used_pools.add(server)

    return used_pools

def linreg(data):
    ydata = [p[-1] for p in data]
    xdata = [[1] + p[:-1] for p in data]
    l = 0.00001
    n = len(xdata[0])
    Z = np.matrix(xdata)
    wreg = (Z.T * Z + np.identity(n)*l).I*Z.T*np.matrix(ydata).T
    return [float(d) for d in list(wreg)]

def train_data():
    if np == None:
        return
    while True:
        servers = calc_good_servers()

        global used_pools
        used_pools = servers

        data = []
        for block in blocks_timing:
            if not blocks_actual.get(block, None):
                continue
            point = [block.get(server, 10000) for server in servers]
            point.append(blocks_actual.get(block))
            data.append(point)

        global weights
        if data:
            weights = linreg(data)

        gevent.sleep(60*5)

gevent.spawn(train_data)
gevent.spawn(poke_deepbit)
gevent.spawn(check_learning)
