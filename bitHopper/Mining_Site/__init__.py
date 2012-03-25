import bitHopper.Tracking
import bitHopper.util
import bitHopper.Network
import json, logging

def mine():
    """
    Function that does basic handling of work requests
    """
    try:
        rpc_request = json.loads(request.data)
    except ValueError, e:
        return bitHopper.util.error_rpc()
        
    #Check for valid rpc_request
    if not bitHopper.util.validate_rpc(rpc_request):
        return bitHopper.util.error_rpc()
        
    #If getworks just feed them data
    if rpc_request['params'] == []:
        #TODO, pass in headers
        content, headers = bitHopper.Network.get_work()
    
    #Otherwise submit the work unit
    else:
        content, headers = bitHopper.Network.submit_work(rpc_request)
        
    return content
