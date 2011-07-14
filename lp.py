#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import bitHopper
import pool
import work
import json
import exceptions

from twisted.internet import reactor, defer

lp_set = False
@defer.inlineCallbacks
def update_lp(response):
    bitHopper.log_msg("LP triggered from server " + bitHopper.get_server())
    global lp_set

    if response == None:
        defer.returnValue(None)

    try:
        finish = Deferred()
        response.deliverBody(work.WorkProtocol(finish))
        body = yield finish
    except Exception, e:
        bitHopper.log_msg('Reading LP Response failed')
        lp_set = True
        defer.returnValue(None)

    try:
        message = json.loads(body)
        value =  message['result']
        #defer.returnValue(value)
    except exceptions.ValueError, e:
        bitHopper.log_msg("Error in json decoding, Probably not a real LP response")
        lp_set = True
        bitHopper.log_dbg(body)
        defer.returnValue(None)

    pool.update_api_servers()
    current = bitHopper.get_server()
    bitHopper.select_best_server()
    if current == bitHopper.get_server():
        bitHopper.log_dbg("LP triggering clients manually")
        bitHopper.lp_callback()
        lp_set = False 
        
    defer.returnValue(None)

def clear_lp():
    global lp_set
    lp_set = False

def set_lp(url, check = False):
    global lp_set
    if check:
        return not lp_set

    if lp_set:
        return

    server = pool.get_entry(pool.get_current())
    if url[0] == '/':
        lp_address = str(server['mine_address']) + str(url)
    else:
        lp_address = str(url)
    bitHopper.log_msg("LP Call " + lp_address)
    lp_set = True
    try:
        work.jsonrpc_lpcall(bitHopper.get_lp_agent(),server, lp_address, update_lp)
    except Exception,e :
        bitHopper.log_dbg('set_lp error')
        bitHopper.log_dbg(e)
