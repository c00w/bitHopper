from bitHopper.Website import app, flask
import btcnet_info
import bitHopper.Configuration.Workers
from bitHopper.Logic.ServerLogic import get_current_servers
from bitHopper.Tracking.Tracking import get_hashrate
import logging
import json
from flask import Response
    
@app.route("/data", methods=['POST', 'GET'])
def data():
    response = {}
    response['current'] = ', '.join([s.name for s in get_current_servers()])
    response['mhash'] = get_hashrate() 
    response['diffs'] = ''
    response['sliceinfo'] = None
    response['servers'] = []
    response['user'] = None
    
    return Response(json.dumps(response), mimetype='text/json') 
