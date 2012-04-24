"""
Stub for networking module
"""

import httplib2, logging, traceback, json, base64
import bitHopper.Logic
import bitHopper.Tracking as Tracking
import ResourcePool
from bitHopper.util import rpc_error
import btcnet_info
import socket
    
i = 0
def _make_http( timeout = None):
    """
    Magic method that makes an httplib2 object
    """
    configured_timeout = 5
    if not timeout:
        timeout = configured_timeout
        
    return httplib2.Http(disable_ssl_certificate_validation=True, timeout=timeout)
        
http_pool = ResourcePool.Pool(_make_http)
        
    
            
def request( url, body = '', headers = {}, method='GET', timeout = None):
    """
    Generic httplib2 wrapper function
    """
    
    if 'Connection' not in headers:
        headers['Connection'] = 'close'
    
    with http_pool(url, timeout=timeout) as http:
        headers, content = http.request( url, method, headers=headers, body=body)
    return content, headers
    
def send_work( url, worker, password, headers={}, body=[], timeout = None):
    """
    Does preproccesing and header setup for sending a work unit
    """
    if not url:
        return None, None
    
    body = json.dumps(body, ensure_ascii = True)
    headers['Authorization'] = "Basic " +base64.b64encode(worker+ ":" + password).replace('\n','')
    headers['Content-Type'] = 'application/json'
    #headers['connection'] = 'keep-alive'
    if 'http' not in url:
        url = 'http://' + url
    
    return request(url, body = body, headers= headers, method='POST', timeout = timeout)

def get_work( headers = {}):
    """
    Gets a work item
    """
    while True:
        server, username, password = bitHopper.Logic.get_server()
        url = btcnet_info.get_pool(server)['mine.address']
        request = {'params':[], 'id':1, 'method':'getwork'}
        
        try:
            content, server_headers = send_work( url, username, password, headers, request)
        except socket.error:
            content, server_headers = None, None
        except:
            logging.error(traceback.format_exc())
            content, server_headers = None, None
            
        if not content:
            bitHopper.Logic.lag(server, username, password)
            continue
            
        Tracking.add_work_unit(content, server, username, password)
        Tracking.headers(server_headers, server)
            
        return content, server_headers
            
def submit_work(rpc_request, headers = {}):
    """
    Submits a work item
    """
    server, username, password = bitHopper.Tracking.get_work_unit(rpc_request)
        
    if not server:
        return rpc_error('Merkle Root Expired'), {}
        
    url = btcnet_info.get_pool(server)['mine.address']
    if not url:
        logging.error('NO URL FOR %s', server)
        return rpc_error('No Url for pool'), {}
        
    content, server_headers = bitHopper.Network.send_work(url, username, password, headers = headers, body = rpc_request['params'])
    
    Tracking.add_result(content, server, username, password)
    Tracking.headers(server_headers, server)
    
    return content, server_headers
    
