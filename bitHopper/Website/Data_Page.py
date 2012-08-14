from bitHopper.Website import app, flask
import btcnet_info
import bitHopper.Configuration.Workers
from bitHopper.Logic.ServerLogic import get_current_servers
from bitHopper.Tracking.Tracking import get_hashrate
import logging
import json
import btcnet_info
from flask import Response
 
def transform_data(servers):
    for server in servers:
        item = {}
        for value in ['name', 'role', 'shares']:
            if getattr(server, value) != None:
                item[value] = getattr(server, value)
            else:
                item[value] = 'undefined'
        item['payout'] = 0.0
        item['expected_payout'] = 0.0
        yield item
   
@app.route("/data", methods=['POST', 'GET'])
def data():
    response = {}
    response['current'] = ', '.join([s.name for s in get_current_servers()])
    response['mhash'] = get_hashrate() 
    response['diffs'] = ''
    response['sliceinfo'] = None
    response['servers'] = list(transform_data(btcnet_info.get_pools())) 
    print response['servers']
    response['user'] = None
    
    return Response(json.dumps(response), mimetype='text/json') 
