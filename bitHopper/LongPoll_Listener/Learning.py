import random
import btcnet_info
import gevent
import logging

import bitHopper.Logic
import bitHopper.Network

blocks_timing = {}
blocks_calculated = {}
blocks_actual = {}

#wait for these pools before calculating results
used_pools = ['deepbit']
weights = [0, 1]

def learn_block(blocks, current_block):
    print 'learn_block called'
    #import block data
    for block in blocks:
        if block not in blocks_timing:
            blocks_timing[block] = blocks[block]

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
    if sum(vec_mult(weights, extract_vector(current_block))) > 0:
        print 'triggered'
        btcnet_info.get_pool('deepbit').namespace.get_node('shares').set_value(0)
        #Reset shares on deepbit
        block_calculated[current_block] = 1
    else:
        block_calculated[current_block] = 0

def check_learning():
    print 'Check learning started'
    while True:
        gevent.sleep(60)
        deepbit_blocks = btcnet_info.get_pool('deepbit').blocks
        for block in blocks_timing:
            if block not in blocks_actual:
                block_actual[block] = 1 if block in deepbit_blocks else 0
                print 'Block %s has training value %s' % (block, block_actual[block])
                print 'deepbit_blocks'

gevent.spawn(check_learning)

#Connect to deepbit if possible    
def poke_deepbit():
    choices = list(bitHopper.Logic.generate_tuples('deepbit'))
    if len(choices) == 0:
        logging.info('No workers for deepbit. Disabling machine learning') 
        return
    server, username, password = random.choice(choices)
    url = btcnet_info.get_pool(server)['mine.address']
    bitHopper.Network.send_work(url, username, password)

gevent.spawn(poke_deepbit)

