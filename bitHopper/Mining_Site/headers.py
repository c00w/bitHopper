"""
Functions for manipulating headers for bitHopper
"""


def clean_headers_client(header):
    """
    Only allows through headers which are safe to pass to the server
    """
    valid = ['user_agent', 'x-mining-extensions', 'x-mining-hashrate']
    for name, value in header.items():
        if name.lower() not in valid:
            del header[name]
        else:
            del header[name]
            header[name.lower()] = value
        if name.lower() == 'x-mining-extensions':
            allowed_extensions=['midstate', 'rollntime']
            header[name.lower()] = ' '.join([
                x for x in header[name.lower()].split(' ') if
                x in allowed_extensions])
    return header
    
def clean_headers_server(header):
    """
    Only allows through headers which are safe to pass to the client
    """
    valid = ['content-length', 'content-type', 'x-roll-ntime', 
             'x-reject-reason', 'noncerange']
    for name, value in header.items():
        if name.lower() not in valid:
            del header[name]
        else:
            del header[name]
            header[name.lower()] = value
    return header
        
    
def get_headers(environ):
    """
    Returns headers from the environ
    """
    headers = {}
    for name in environ:
        if name[0:5] == "HTTP_":
            headers[name[5:]] = environ[name]
    return headers
