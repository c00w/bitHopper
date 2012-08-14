import bitHopper.Database
import bitHopper.Database.Commands
import btcnet_info
import logging, time, traceback, gevent
import bitHopper.Configuration.Pools
from speed import Speed

def get_diff(pool):
    coin = btcnet_info.get_pool(pool)
    if coin:
        coin = coin.coin
    else:
        coin = 'btc'
    return float(btcnet_info.get_difficulty(coin))

getworks = None
accepted = None
rejected = None
hashrate = Speed()

def build_dict():
    """
    Returns a dict with tuples of getworks, accepted, reject, priority, percentage
    """
    __patch()
    res = {}
    for key in getworks:
        server, username, password, diff = key
        if key not in accepted:
            accepted[key] = 0
        if key not in rejected:
            rejected[key] = 0
        if server not in res:
            res[server] = {}
        name = ":".join([shorten(username), password])
        if name not in res[server]:
            res[server][name] = [0, 0, 0, 0, 0]
        res[server][name][0] += getworks[key]
        res[server][name][1] += accepted[key]
        res[server][name][2] += rejected[key]
        res[server][name] = map(int, res[server][name])
    return res

def __patch():
    global getworks, accepted, rejected
    
    if getworks == None:
        getworks, accepted, rejected = load_from_db()
        gevent.spawn(looping_store)
        
def shorten(name):
    """
    Shortens a name and adds some ellipses
    """
    if len(name) > 10:
        name = name[:10] + '...'
    return name
    
def looping_store():
    """
    repeatedly calls store_current and sleep in between
    """
    while True:
        gevent.sleep(30)
        try:
            store_current()
        except:
            logging.error(traceback.format_exc())
    
def store_current():
    """
    Stores the current logs in the database
    """
    for key, getwork_c in getworks.items():
        accepted_c = accepted.get(key, 0)
        rejected_c = rejected.get(key, 0)
        #Extract key information
        server = key[0]
        username = key[1]
        password = key[2]
        difficulty = key[3]
        timestamp = time.asctime(time.gmtime())
        
        #If this isn't the current difficulty we are not responsible for storing it
        try:
            if get_diff(server) != difficulty:
                continue
        except:
            logging.error(traceback.format_exc())
            continue
            
        #Do an update
        sql = "UPDATE Statistics SET Getworks = %s, Accepted = %s, Rejected = %s, Timestamp = '%s' WHERE Server = '%s' AND Username = '%s' AND Password = '%s' AND Difficulty = %s" % (getwork_c, accepted_c, rejected_c, timestamp, server, username, password, difficulty)
        bitHopper.Database.execute(sql)
        
        #Check if we actually updated something
        result = bitHopper.Database.execute('SELECT Getworks from Statistics WHERE Server = "%s" AND Username = "%s" AND Password = "%s" AND Difficulty = %s' % (server, username, password, difficulty))
        result = list(result)
        
        #If we didn't do an insert
        if len(result) == 0:
            sql = "INSERT INTO Statistics (Server, Username, Password, Difficulty, Timestamp, Getworks, Accepted, Rejected) VALUES ('%s', '%s', '%s', %s, '%s', %s, %s, %s)" % (server, username, password, difficulty, timestamp, getwork_c, accepted_c, rejected_c)
            bitHopper.Database.execute(sql)
        
            
        
def load_from_db():
    """
    Load workers from database
    """
    columns = [ 'Server TEXT',
                'Username TEXT',
                'Password TEXT', 
                'Difficulty REAL',
                'Timestamp TEXT',
                'Getworks REAL',
                'Accepted REAL',
                'Rejected REAL']
    
    bitHopper.Database.Commands.Create_Table('Statistics', columns)
    results = bitHopper.Database.execute('Select Server, Username, Password, Difficulty, Getworks, Accepted, Rejected FROM Statistics')
    
    getworks = {}
    accepted = {}
    rejected = {}
    
    for server, username, password, difficulty, getworks_v, accepted_v, rejected_v in results:
        key = (server, username, password, difficulty)
        getworks[key] = getworks_v
        accepted[key] = accepted_v
        rejected[key] = rejected_v
        
    return getworks, accepted, rejected

def get_key(server, username, password):
    """
    Builds a key to access the dictionaries
    """
    difficulty = get_diff(server)
    key = (server, username, password, difficulty)
    return key
    
def add_getwork(server, username, password):
    """
    Adds a getwork to the database
    """
    __patch()
    key = get_key(server, username, password)
    if key not in getworks:
        getworks[key] = 0
    getworks[key] += 1
    username = shorten(username)
    logging.info('Getwork: %s:%s@%s' % (username, password, server))
    

def add_accepted(server, username, password):
    """
    Adds an accepted result to the database
    """
    __patch()
    key = get_key(server, username, password)
    if key not in accepted:
        accepted[key] = 0
    accepted[key] += 1
    username = shorten(username)
    hashrate.add_shares(1) 
    logging.info('Accepted: %s:%s@%s' % (username, password, server))
    
def add_rejected(server, username, password):
    """
    Adds a rejected result to the database
    """
    __patch()
    key = get_key(server, username, password)
    if key not in rejected:
        rejected[key] = 0
    rejected[key] += 1
    username = shorten(username)
    hashrate.add_shares(1)
    logging.info('Rejected: %s:%s@%s' % (username, password, server))

def get_hashrate():
    return hashrate.get_rate()
