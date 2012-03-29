import bitHopper.Tracking
import bitHopper.util
import bitHopper.Network
import json, logging

def _read_all(fp):
    a = ''
    for b in fp:
        a += b
    return a
    
def clean_headers(header):
    valid = ['user_agent', 'x-mining-extensions']
    for name, value in header.items():
        if name.lower() not in valid:
            del header[name]
        else:
            del header[name]
            header[name.lower()] = value
    return header
        
    
def _get_headers(environ):
    headers = {}
    for name in environ:
        if name[0:5] == "HTTP_":
            headers[name[5:]] = environ[name]
    return headers
    
def mine(environ, start_response):
    """
    Function that does basic handling of work requests
    """
    
    #Do this at the top for now so we allways call it.
    start_response('200 OK', [])
    
    #This should never cause an error
    if 'wsgi.input' not in environ:
        return bitHopper.util.rpc_error('No body passed')
        
    #Read everything out
    request = _read_all(environ['wsgi.input'])
    try:
        rpc_request = json.loads(request)
    except ValueError, e:
        return bitHopper.util.rpc_error()
        
    #Check for valid rpc_request
    if not bitHopper.util.validate_rpc(rpc_request):
        return bitHopper.util.rpc_error()
        
    #Get client headers
    headers = _get_headers(environ)
    #Remove everything we don't want
    headers = clean_headers(headers)
    
    #If getworks just feed them data
    if rpc_request['params'] == []:
        #TODO, pass in headers
        content, headers = bitHopper.Network.get_work(headers = headers)
    
    #Otherwise submit the work unit
    else:
        content, headers = bitHopper.Network.submit_work(rpc_request)
    
    return content
