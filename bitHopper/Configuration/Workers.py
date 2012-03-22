#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

"""
File for configuring multiple workers
"""
import bitHopper.Database.Commands
import bitHopper.Database
workers = None

def __patch():
    global workers
    if not workers:
        workers = load_from_db()
        
def load_from_db():
    columns = [ 'Server TEXT',
                'Username TEXT',
                'Password TEXT']
    
    bitHopper.Database.Commands.Create_Table('Workers', columns)
    results = bitHopper.Database.execute('SELECT Server, Username, Password FROM Workers')
    
    workers = {}
    
    for server, username, password in result:
        if server not in workers:
            workers[server]  = set()
        workers[server].add((username, password))
        
    return workers
    
def get_worker_from(pool):
    pass
    
    
    
        

    
    
