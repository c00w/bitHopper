#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

"""
File for configuring multiple pools
Things such as priority, percentage etc...
"""
import bitHopper.Database.Commands
import bitHopper.Database
import random
pools = None

def __patch():
    global pools
    if pools == None:
        pools = load_from_db()
        
def load_from_db():
    """
    Load pools from database
    """
    columns = [ 'Server TEXT',
                'Percentage INTEGER',
                'Priority INTEGER']
    
    bitHopper.Database.Commands.Create_Table('Pools', columns)
    results = bitHopper.Database.execute('SELECT Server, Percentage, Priority FROM Pools')
    
    pools = {}
    
    for server, percentage, priority in results:
        if server not in pools:
            pools[server]  = {'percentage':percentage, 'priority':priority}
        else:
            #Really should delete the duplicate entry
            pass
        
    return pools
    
def len_pools():
    """
    Return the number of pools with special things
    """
    __patch()
    return len(pools)
        
def set_priority(server, prio):
    """
    Sets pool priority, higher is better
    It also sets percentage if the server does not exist
    """
    __patch()
    if server not in pools:
        pools[server] = {'priority':0, 'percentage':0}
    pools[server]['priority'] = int(prio)
    bitHopper.Database.execute("INSERT INTO Pools VALUES ('%s',%s,%s)" % (server, int(prio), 0))
    
def get_priority(server):
    """
    Gets pool priority
    """
    __patch()
    if server not in pools:
        return 0
    return pools[server]['priority']
    
def set_percentage(server, perc):
    """
    Sets pool percentage, the amount of work we should always feed to the server
    It also sets priority if the server does not exist
    """
    __patch()
    if server not in pools:
        pools[server] = {'priority':0, 'percentage':0}
    pools[server]['percentage'] = int(perc)
    bitHopper.Database.execute("INSERT INTO Pools VALUES ('%s',%s,%s)" % (server, 0, int(perc)))
    
def get_percentage(server):
    """
    Gets pool percentage
    """
    __patch()
    if server not in pools:
        return 0
    return pools[server]['percentage']
    
def percentage_server():
    """
    Gets all server with a percentage
    """
    for server, info in pools.items():
        if info['percentage'] > 0:
            yield server, info['percentage']

        

    
    
