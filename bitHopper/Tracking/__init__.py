from getwork_store import Getwork_Store
from bitHopper.util import extract_merkle, extract_result
import Tracking
__store = False

def __patch():
    global __store
    if not __store:
        __store = Getwork_Store()

def add_work_unit(content, server, username, password):
    """
    Does wrapping and stores the submission
    """
    __patch()
    merkle_root = extract_merkle(content)
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
    result = extract_result(content)
    print result
    if result.lower() in ['false']
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
        return (None, None, None)
    auth = __store.get(merkle_root)
    if not auth:
        return (None, None, None)
    return auth
