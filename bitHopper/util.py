
def validate_rpc(content):
    """
    Validates that this is a valid rpc message for our purposes
    """
    required = {'params':None, 'id':None, 'method':'getwork'}
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
    if not validate_rpc(content):
        return None
    merkle = content['params']['data'][72:136]
    return merkle
