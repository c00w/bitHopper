import logging, json
import bitHopper.Tracking
import bitHopper.util
import bitHopper.network

from flask import *

app = Flask(__name__, template_folder='./templates', 
            static_folder = './static')
app.Debug = False

def error_rpc(message = 'Invalid Request'):
    return json.dumps({"result":None, 'error':{'message':message}, 'id':1})

@app.teardown_request
def teardown_request_wrap(exception):
    """
    Prints tracebacks and handles bugs
    """
    if exception:
        logging.error(traceback.format_exc())
        else:
            return json.dumps({"result":None, 'error':{'message':'Invalid request'}, 'id':1})
            
@app.route("/", methods=['POST'])
@app.route("/mine", methods=['POST','GET'])
def mine():
    try:
        rpc_request = json.loads(request.data)
    except ValueError, e:
        return error_rpc()
        
    #Check for valid rpc_request
    if not bitHopper.util.validate_rpc(rpc_request):
        return error_rpc()
        
    #If getworks just feed them data
    if rpc_request['params'] = []:
        #TODO, pass in headers
        return bitHopper.Network.get_work()
        
    server, username, password = bitHopper.Tracking.get_work_unit(rpc_request)
    
    if not server:
        return error_rpc('Merkle Root Expired')
        
    url = btcnet_info.get_pool(server).mine.address
    if not url:
        logging.error('NO URL FOR %s', server)
        return error_rpc('Merkle Root Expired')
        
    return bitHopper.Network.send_work(url, username, password)
        
    
