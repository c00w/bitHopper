import bitHopper.Database
import bitHopper.Database.Commands
import btcnet_info
import logging

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

def __patch():
    global getworks, accepted, rejected
    
    if getworks == None:
        getworks, accepted, rejected = load_from_db()
        
def shorten(name):
    if len(name) > 10:
        name = name[:10] + '...'
    return name
        
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
    global getworks
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
    global accepted
    key = get_key(server, username, password)
    if key not in accepted:
        accepted[key] = 0
    accepted[key] += 1
    username = shorten(username)
    logging.info('Accepted: %s:%s@%s' % (username, password, server))
    
def add_rejected(server, username, password):
    """
    Adds a rejected result to the database
    """
    __patch()
    global rejected
    key = get_key(server, username, password)
    if key not in rejected:
        rejected[key] = 0
    rejected[key] += 1
    username = shorten(username)
    logging.info('Rejected: %s:%s@%s' % (username, password, server))
