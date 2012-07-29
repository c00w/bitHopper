"""
Utility functions for bitHopper
"""

import json, logging

def validate_rpc(content):
    """
    Validates that this is a valid rpc message for our purposes
    """
    if type(content) != type({}):
        return False
    required = {'params':None, 'id':None, 'method':'getwork'}
    for key, value in required.items():
        if key not in content:
            return False
        if value and content[key] != value:
            return False
    
    return True
    
def validate_rpc_recieved(content):
    """
    Validates that this is a valid rpc message for our purposes
    """
    required = {'result':None, 'id':None, 'error':None}
    for key, value in required.items():
        if key not in content:
            return False
        if value and content[key] != value:
            return False
    
    return True
    
def extract_merkle(content):
    """
    extracts the merkle root
    """
    if 'params' not in content:
        logging.info('Malformed sendwork')
        return None
    if len(content['params']) != 1:
        logging.info('Malformed sendwork')
        return None
    if len(content['params'][0])<136:
        logging.info('Malformed sendwork')
        return None
        
    merkle = content['params'][0][72:136]
    return merkle

def extract_merkle_recieved(content):
    """
    extracts the merkle root for a message we recieved
    """
    if not validate_rpc_recieved(content):
        return None
    merkle = content['result']['data'][72:136]
    return merkle
    
def extract_result(content):
    """
    extracts the result
    """
    result = content['result']
    return result
    

def rpc_error(message = 'Invalid Request'):
    """
    Generates an rpc error message
    """
    return json.dumps({"result":None, 'error':{'message':message}, 'id':1})

