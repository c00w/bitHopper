"""
Stub for networking module
"""

import httplib2
import bitHopper.Logic, bitHopper.Tracking
from . import ResourcePool

    
def submit_work(work):
    pass
    
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
    with http_pool(url, timeout=timeout) as http:
        headers, content = http.request( url, method, headers=headers, body=body)
    return content, headers
    
def send_work( url, worker, password, headers={}, body=[]):
    """
    Does preproccesing and header setup for sending a work unit
    """
    if not url:
        return None, None
    
    body = json.dumps(body, ensure_ascii = True)
    header['Authorization'] = "Basic " +base64.b64encode(worker+ ":" + password).replace('\n','')
    header['Content-Type'] = 'application/json'
    header['connection'] = 'keep-alive'
    
    return request(url, body = body, headers= headers)

def get_work( headers = {}):
    """
    Gets a work item
    """
    while True:
        server, username, password = Logic.get_server()
        url = btcnet_info.get_pool('url').mine.address
        request = {'params':[], 'id':1, 'method':'getwork'}
        
        try:
            content, headers = send_work( url, username, password, headers, request)
        except:
            logging.error(traceback.format_exc())
            content, headers = None, None
            
        if not content:
            Logic.lag(server, username, password)
            continue
            
        Tracking.add_work_unit(content, server, username, password)
            
        return content, headers
            
