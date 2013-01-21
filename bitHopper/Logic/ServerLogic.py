"""
File implementing the actuall logic for the business side
"""

import btcnet_info
import bitHopper.Configuration.Workers as Workers
import bitHopper.Configuration.Pools as Pools
import bitHopper.LaggingLogic
import logging, traceback, gevent, random

def _select(item):
    """
    Selection utility function
    """
    global i
    i = i + 1 if i < 10**10 else 0
    if len(item) == 0:
        raise ValueError("No valid pools")
    return item[i % len(item)]

def difficulty_cutoff(source):
    """
    returns the difficulty cut off for the pool
    """

    diff = btcnet_info.get_difficulty(source.coin)
    btc_diff = btcnet_info.get_difficulty(source.coin)
    if not diff:
        return 0
        #while not diff:
        #    gevent.sleep(0)
        #    diff = btcnet_info.get_difficulty(source.coin)

    diff = float(diff)
    btc_diff = float(btc_diff)

    #Propositional Hopping
    if source.payout_scheme in ['prop']:
        return diff * 0.435

    #Score Hopping
    if source.payout_scheme in ['score']:
        c = source.mine.c if source.mine and source.mine.c else 300
        c = float(c)
        hashrate = float(source.rate) / (10. ** 9) if source.rate else 1
        hopoff = btc_diff * (0.0164293 + 1.14254 / (1.8747 * (btc_diff / (c * hashrate)) + 2.71828))
        return hopoff

def highest_priority(source):
    """
    Filters pools by highest priority
    """
    max_prio = 0
    pools = list(source)
    for pool in pools:
        name = pool.name
        if not name:
            continue
        if Pools.get_priority(name)>max_prio:
            max_prio = Pools.get_priority(name)

    for pool in pools:
        name = pool.name
        if not name:
            continue
        if Pools.get_priority(name)>=max_prio:
            yield pool

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
        if scheme.lower() in ['pps', 'smpps', 'pplns', 'dgm']:
            yield site

        if scheme.lower() in ['prop', 'score']:

            #Check if we have a share count
            shares = site.shares
            if not shares:
                continue

            shares = float(shares)
            if shares < difficulty_cutoff(site):
                yield site

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
            if len(list(bitHopper.LaggingLogic.filter_lag([(name, user, password)]))):
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
        if pool.payout_scheme.lower() in ['pplns', 'smpps', 'pps', 'dgm']:
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
                yield pool
        return

    #Select a backup pool
    backup = list(filter_secure(pools))
    if backup:
        for x in backup:
            yield x
        return

    raise ValueError("No valid pools configured")

def generate_servers():
    """
    Method that generate the best server
    """
    while True:
        rebuild_servers()
        gevent.sleep(5)

filters = [valid_credentials, valid_scheme, highest_priority, filter_best]

def rebuild_servers():
    """
    The function the rebuilds the set of servers
    """
    try:
        global Servers
        servers = btcnet_info.get_pools().copy()
        for filter_f in filters:
            servers = filter_f(servers)
        Servers = list(servers)
    except ValueError as Error:
        logging.warn(Error)
    except Exception as Error:
        logging.error(traceback.format_exc())

def get_server():
    """
    Returns an iterator of valid servers
    """
    perc_map = []
    map_ods = 0.0
    percentage = Pools.percentage_server()
    for server, percentage in percentage:
        for perc in range(percentage):
            perc_map.append(server)
            map_ods += 0.01
    if random.random() < map_ods:
        return random.choice(perc_map)

    return _select(Servers).name

def get_current_servers():
    return Servers

i = 1
Servers = set()
gevent.spawn(generate_servers)
gevent.sleep(0)
