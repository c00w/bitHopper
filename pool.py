#!/bin/python

import json
import time
from jsonrpc import ServiceProxy

from twisted.web import server, resource
from twisted.web.client import getPage
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

access = None
#access = ServiceProxy("http://19ErX2nDvNQgazXweD1pKrjbBLKQQDM5RY:x@mining.eligius.st:8337")
servers = {
        'bclc':{'time':time.time(), 'shares':0, 'name':'bitcoins.lc', 'mine_address':'bitcoins.lc:8080', 'user':'FSkyvM', 'pass':'xndzEU'},
        'mtred':{'time':time.time(), 'shares':0, 'name':'mtred',  'mine_address':'mtred.com:8337', 'user':'scarium', 'pass':'x'}}
current_server = 'mtred'
difficulty = 1563027.996116

def select_best_server():
    server_name = None
    min_shares = 10**9
    
    for server in servers:
        if servers[server]['shares']< min_shares:
            min_shares = servers[server]['shares']
            server_name = server
    current_server = server_name
    access = ServiceProxy("http://" + server['user']+ ":" + server['pass'] + "@" + server['mine_address'])
    return

def server_update():
    if current_server == None:
        select_best_server()
        return

    if current_server not in servers:
        return

    if servers[current_server]['shares'] > difficulty * .40:
        select_best_server()
        return

def bclc_sharesResponse(response):
    info = json.load(response)
    round_shares = int(info['round_shares'])
    if 'bclc' not in server:
        servers['bclc'] = {'time':time.time(), 'shares':round_shares, 'name':'bitcoins.lc', 'mine_address':'bitcoins.lc:8080', 'user':'FSkyvM', 'pass':'xndzEU'}
    else:
        servers['bclc']['time'] = time.time()
        servers['bclc']['shares'] = round_shares
    server_update()
    
def mtred_sharesResponse(response):
    info = json.load(response)
    round_shares = int(info['server']['servers']['n0']['roundshares'])
    if 'bclc' not in server:
        servers['mtred'] = {'time':time.time(), 'shares':round_shares, 'name':'mtred', 'mine_address':'mtred.com:8337', 'user':'scarium', 'pass':'x'}
    else:
        servers['mtred']['time'] = time.time()
        servers['mtred']['shares'] = round_shares
    server_update()

def bclc_getshares():
    getPage('https://www.bitcoins.lc/stats.json').addCallback(bclc_sharesResponse)

def mtred_getshares():
    getPage('https://mtred.com/api/user/key/d91c52cfe1609f161f28a1268a2915b8').addCallback( mtred_sharesResponse )

def update_servers():
    global servers
    bclc_getshares()
    mtred_getshares()


def jsonrpc_getwork(data):
    if access == None:
        if current_server == None:
            server_update()
            current_server = select_best_server()
            
        server = server[current_server]
        access = ServiceProxy("http://" + server['user']+ ":" + server['pass'] + "@" + server['mine_address'])
    v = access.getwork()
    return v



class Simple(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        return "<html></html>"

    def render_POST(self, request):
        rpc_request = json.load(request.content)
        print rpc_request
        #check if they are sending a valid message
        if rpc_request['method'] != "getwork":
            return json.dumps({'result':None, 'error':'Not supported', 'id':rpc_request['id']})


        #Check for data to be validated
        data = rpc_request['params']
        data = jsonrpc_getwork(data)
        response = json.dumps({"result":data,'error':None,'id':rpc_request['id']})
        print response
        return response


    def getChild(self,name,request):
        return self


def main():

    site = server.Site(Simple())
    reactor.listenTCP(8337, site)
    update_call = LoopingCall(update_servers)
    update_call.start(20)
    reactor.run()

if __name__ == "__main__":
    main()

