import bitHopper.Database
import bitHopper.Database.Commands
import btcnet_info

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
    global workers, accepted, rejected
    
    if getworks == None:
        workers, accepted, rejected = load_from_db()
        
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

def get_key(server, username, pool):
    """
    Builds a key to access the dictionaries
    """
    difficulty = get_diff(server)
    key = (server, username, password, difficulty)
    return key
    
def add_getwork(server, username, pool):
    """
    Adds a getwork to the database
    """
    __patch()
    global getworks
    key = get_key(server, username, pool)
    if key not in getworks:
        getworks[key] = 0
    getworks[key] += 1
    

def add_accepted(server, username, pool):
    """
    Adds an accepted result to the database
    """
    __patch()
    global accepted
    key = get_key(server, username, pool)
    if key not in accepted:
        accepted[key] = 0
    accepted[key] += 1
    
def add_rejected(server, username, pool):
    """
    Adds a rejected result to the database
    """
    __patch()
    global rejected
    key = get_key(server, username, pool)
    if key not in rejected:
        rejected[key] = 0
    rejected[key] += 1
    
