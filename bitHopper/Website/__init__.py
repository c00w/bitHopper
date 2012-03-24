import logging, json
import bitHopper.Tracking
import bitHopper.util
import bitHopper.Network

import flask

app = flask.Flask(__name__, template_folder='bitHopper/templates', 
            static_folder = 'bitHopper/static')
app.Debug = False

@app.teardown_request
def teardown_request_wrap(exception):
    """
    Prints tracebacks and handles bugs
    """
    if exception:
        logging.error(traceback.format_exc())
        return json.dumps({"result":None, 'error':{'message':'Invalid request'}, 'id':1})
            
@app.route("/", methods=['POST'])
@app.route("/mine", methods=['POST','GET'])
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
        
    
