from getwork_store import Getwork_Store
from bitHopper.util import *
import Tracking
import bitHopper.LongPoll_Listener
import json, logging

__store = False

def __patch():
    global __store
    if not __store:
        __store = Getwork_Store()
        
def headers(headers, server):
    """
    Deals with headers from the server, mainly for LP
    but we could do other things
    """
    for k, v in headers.items():
        if k.lower() == 'x-long-polling':
            bitHopper.LongPoll_Listener.add_address(server, v)

def add_work_unit(content, server, username, password):
    """
    Does wrapping and stores the submission
    """
    __patch()
    try:
        content = json.loads(content)
    except:
        return
    merkle_root = extract_merkle_recieved(content)
    if not merkle_root:
        return
    auth = (server, username, password)
    __store.add(merkle_root, auth)
    Tracking.add_getwork(server, username, password)
    
def add_result(content, server, username, password):
    """
    Does wrapping and stores the result
    """
    __patch()
    
    try:
        content = json.loads(content)
    except:
        return
    
    result = extract_result(content)
    if result in [False]:
        Tracking.add_rejected(server, username, password)
    else:
        Tracking.add_accepted(server, username, password)
    
    
def get_work_unit(content):
    """
    Does wrapping and returns the result
    """
    __patch()
    
    merkle_root = extract_merkle(content)
    if not merkle_root:
        logging.info('No merkle root found')
        return (None, None, None)
    auth = __store.get(merkle_root)
    if not auth:
        logging.info('Root %s not in %s', merkle_root, __store)
        return (None, None, None)
    return auth
