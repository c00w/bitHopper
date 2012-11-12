from bitHopper.Website import app, flask
import btcnet_info
import bitHopper.Configuration.Workers
from bitHopper.Logic.ServerLogic import get_current_servers, valid_scheme
from bitHopper.Tracking.Tracking import get_hashrate
import logging
import json
import btcnet_info
from flask import Response
 
def transform_data(servers):
    for server in servers:
        item = {}
        for value in ['name', 'shares', 'coin']:
            if getattr(server, value) != None:
                item[value] = getattr(server, value)
            else:
                item[value] = 'undefined'
        item['shares'] = float(item.get('shares',0)) if item['shares'] != 'undefined' else 'undefined'
        item['payout'] = 0.0
        item['expected_payout'] = 0.0
        item['role'] = 'mine/backup' if server in valid_scheme([server]) else 'info'
        yield item
   
@app.route("/data", methods=['POST', 'GET'])
def data():
    response = {}
    response['current'] = ', '.join([s.name for s in get_current_servers()])
    response['mhash'] = get_hashrate() 
    response['diffs'] = dict([(coin.name, float(coin.difficulty)) for coin in btcnet_info.get_coins() if coin.difficulty])
    response['sliceinfo'] = None
    response['servers'] = list(transform_data(btcnet_info.get_pools())) 
    response['user'] = None
    
    return Response(json.dumps(response), mimetype='text/json') 
