import bitHopper.Database.Commands
import bitHopper.Database
import random
miners = None

def __patch():
    global miners
    if miners == None:
        miners = load_from_db()

def load_from_db():
    """
    Load miners from database
    """
    columns = [ 'Username TEXT',
                'Password TEXT']

    bitHopper.Database.Commands.Create_Table('Miners', columns)
    results = bitHopper.Database.execute('SELECT Username, Password FROM Miners')

    miners = set()

    for username, password in results:
        miners.add((username, password))

    return miners

def len_miners():
    """
    Returns the length of the worker table
    """
    __patch()
    return len(miners)

def get_miners():
    """
    Returns a list of workers
    """
    __patch()
    miners_l = list(miners)
    miners_l.sort()
    return miners_l

def valid(username, password):
    """
    Check if a username, password combination is valid
    """
    __patch()
    if len(miners) == 0:
        return True
    return (username, password) in miners

def add(username, password):
    """
    Adds a miner into the database and the local cache
    """
    __patch()
    if (username, password) not in miners:
        miners.add((username, password))
        bitHopper.Database.execute("INSERT INTO Miners VALUES ('%s','%s')" % (username, password))

def remove(username, password):
    """
    Removes a miner from the local cache and the database
    """
    __patch()
    if (username, password) not in miners:
        return
    miners.remove((username, password))
    bitHopper.Database.execute("DELETE FROM Miners WHERE Username = '%s' AND Password = '%s'" % (username, password))
