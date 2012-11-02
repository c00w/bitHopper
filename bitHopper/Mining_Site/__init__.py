import bitHopper.Tracking
import bitHopper.util
import bitHopper.Network
import bitHopper.Configuration.Miners
import json, logging, base64
import bitHopper.LongPoll
from headers import *
import traceback
import gevent

def _read_all(fp):
    """
    Reads everything from a file pointer like object
    """
    a = ''
    for b in fp:
        a += b
    return a
    
def getBasicCredentials(both):
    """Parses the HTTP_AUTHORIZATION item for basic credentials"""
    encd = both.split()[-1]
    values = base64.b64decode(encd).split(':', 1)
    if len(values)==2:
        return values[0],values[1]
    return None, None
    
def validate_miner(environ):
    """
    Verifies that the user is a valid miner
    """
    auth_response = environ.get("HTTP_AUTHORIZATION",None)
    if auth_response is None:
        return False
        
    username, password = getBasicCredentials(auth_response)
    if username is None:
        return False
        
    return bitHopper.Configuration.Miners.valid(username, password)
    
def mine(environ, start_response):
    try:
        return mine_real(environ, start_response)
    except:
        logging.error(traceback.format_exc())
        start_response('200 OK', [])
        return bitHopper.util.rpc_error('Unknown Error')
    
def mine_real(environ, start_response):
    """
    Function that does basic handling of work requests
    """
    #If this is an LP, do something different
    if 'longpoll' in environ['PATH_INFO']:
        bitHopper.LongPoll.wait()

    #This should never cause an error
    if 'wsgi.input' not in environ:
        start_response('200 OK', [])
        yield bitHopper.util.rpc_error('No body passed')
        return
        
    #Read everything out
    request = _read_all(environ['wsgi.input'])
    try:
        rpc_request = json.loads(request)
    except ValueError, e:
        start_response('200 OK', [])
        yield bitHopper.util.rpc_error()
        return
        
    #Check for valid rpc_request
    if not bitHopper.util.validate_rpc(rpc_request):
        start_response('200 OK', [])
        yield bitHopper.util.rpc_error()
        return
    
    #Check for a valid username, password
    if not validate_miner(environ):
        start_response('200 OK', [])
        yield bitHopper.util.rpc_error('Invalid Authorisation')
        return
        
    #Get client headers
    headers = get_headers(environ)
    
    #Remove everything we don't want
    headers = clean_headers_client(headers)

    #If getworks just feed them data
    if rpc_request['params'] == []:
        g = gevent.spawn(bitHopper.Network.get_work, headers = headers)
        while True:
            yield ''
            try:
                content, headers = g.get(timeout=0.1)
                break
            except gevent.Timeout:
                pass
    
    #Otherwise submit the work unit
    else:
        g = gevent.spawn(bitHopper.Network.submit_work, rpc_request)
        while True:
            yield ''
            try:
                content, headers = g.get(timeout=0.1)
                break
            except gevent.Timeout:
                pass
    
    headers = clean_headers_server(headers)
    
    #Set Long Polling Header
    headers['x-long-polling'] = '/longpoll'
    headers['Connection'] = 'Keep-Alive'
    
    start_response('200 OK', headers.items())
    yield content
    return
