import bitHopper.Tracking
import bitHopper.util
import bitHopper.Network
import json, logging
import bitHopper.LongPoll
from headers import *
import traceback

def _read_all(fp):
    """
    Reads everything from a file pointer like object
    """
    a = ''
    for b in fp:
        a += b
    return a
    
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
        return bitHopper.util.rpc_error('No body passed')
        
    #Read everything out
    request = _read_all(environ['wsgi.input'])
    try:
        rpc_request = json.loads(request)
    except ValueError, e:
        start_response('200 OK', [])
        return bitHopper.util.rpc_error()
        
    #Check for valid rpc_request
    if not bitHopper.util.validate_rpc(rpc_request):
        start_response('200 OK', [])
        return bitHopper.util.rpc_error()
        
    #Get client headers
    headers = get_headers(environ)
    
    #Remove everything we don't want
    headers = clean_headers_client(headers)
    
    #If getworks just feed them data
    if rpc_request['params'] == []:
        content, headers = bitHopper.Network.get_work(headers = headers)
    
    #Otherwise submit the work unit
    else:
        content, headers = bitHopper.Network.submit_work(rpc_request)
    
    headers = clean_headers_server(headers)
    
    #Set Long Polling Header
    headers['x-long-polling'] = '/longpoll'
    
    start_response('200 OK', headers.items())
    return content
