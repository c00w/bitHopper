#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

"""
File for configuring multiple workers

TODO: FIX ALL THE SQL INJECTIONS. EVERYONE OF THESE THINGS IS FULL OF THEM
"""
import bitHopper.Database.Commands
import bitHopper.Database
workers = None

def __patch():
    global workers
    if workers == None:
        workers = load_from_db()
        
def load_from_db():
    """
    Load workers from database
    """
    columns = [ 'Server TEXT',
                'Username TEXT',
                'Password TEXT']
    
    bitHopper.Database.Commands.Create_Table('Workers', columns)
    results = bitHopper.Database.execute('SELECT Server, Username, Password FROM Workers')
    
    workers = {}
    
    for server, username, password in results:
        if server not in workers:
            workers[server]  = set()
        workers[server].add((username, password))
        
    return workers
    
def get_worker_from(pool):
    """
    Returns a list of workers in the given pool
    In the form of [Server, Username, Password], ...
    """
    __patch()
    if pool not in workers:
        return []
    return workers[pool]
    
def add(server, username, password):
    """
    Adds a worker into the database and the local cache
    """
    __patch()
    if server not in workers:
        workers[server] = set()
    if (username, password) not in workers[server]:
        workers[server].add((username, password))
        bitHopper.Database.execute("INSERT INTO Workers VALUES ('%s','%s','%s')" % (server, username, password))
    
def remove(server, username, password):
    """
    Removes a worker from the local cache and the database
    """
    __patch()
    if server not in workers:
        return
    if (username, password) not in workers[server]:
        return
    workers[server].remove((username, password))
    bitHopper.Database.execute("DELETE FROM Workers WHERE Server = '%s' AND Username = '%s' AND Password = '%s'" % (server, username, password))
        

    
    
