#!/bin/python2.7
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import time
from jsonrpc import ServiceProxy
import socket
import os
import base64
import work

from zope.interface import implements

from twisted.web import server, resource
from twisted.web.client import getPage, Agent
from twisted.web.iweb import IBodyProducer
from twisted.web.http_headers import Headers
from twisted.internet import reactor, threads, defer
from twisted.internet.defer import succeed, Deferred
from twisted.internet.task import LoopingCall
import urllib2
from twisted.internet.protocol import Protocol\

#SET THESE
bclc_user  = "FSkyvM"
bclc_pass = "xndzEU"
mtred_user = 'scarium'
mtred_pass = 'x'
eligius_address = '1AofHmwVef5QkamCW6KqiD4cRqEcq5U7hZ'
btcguild_user = 'c00w_test'
btcguild_pass = 'x'
bitclockers_user = 'flargle'
bitclockers_pass = 'x'
mineco_user = 'c00w.test'
mineco_pass = 'x'
#REALLY

LP_URL = 'non existant adress'

def get_difficulty():
    req = urllib2.Request('http://blockexplorer.com/q/getdifficulty')
    response = urllib2.urlopen(req)
    diff_string = response.read()
    return float(diff_string)

difficulty = get_difficulty()

servers = {
        'bclc':{'time':time.time(), 'shares':0, 'name':'bitcoins.lc', 
            'mine_address':'bitcoins.lc:8080', 'user':bclc_user, 'pass':bclc_pass, 
            'lag':False, 'LP':None},
        'mtred':{'time':time.time(), 'shares':0, 'name':'mtred',  
            'mine_address':'mtred.com:8337', 'user':mtred_user, 'pass':mtred_pass, 
            'lag':False, 'LP':None},
        'btcg':{'time':time.time(), 'shares':10**9, 'name':'BTC Guild',  
            'mine_address':'uscentral.btcguild.com:8332', 'user':btcguild_user, 
            'pass':btcguild_pass, 'lag':False, 'LP':None},
        'eligius':{'time':time.time(), 'shares':difficulty*.41, 'name':'eligius', 
            'mine_address':'mining.eligius.st:8337', 'user':eligius_address, 
            'pass':'x', 'lag':False, 'LP':None},
        'mineco':{'time': time.time(), 'shares': 0, 'name': 'mineco.in',
            'mine_address': 'mineco.in:3000', 'user': mineco_user,
            'pass': mineco_pass, 'lag': False, 'LP': None},
        'bitclockers':{'time': time.time(), 'shares': 0, 'name': 'bitclockers.com',
            'mine_address': 'pool.bitclockers.com:8332', 'user': bitclockers_user,
            'pass': bitclockers_pass, 'lag': False, 'LP': None}
        }

current_server = 'eligius'
json_agent = Agent(reactor)

def select_best_server():
    """selects the best server for pool hopping. If there is not good server it returns eligious"""
    global servers
    global access
    global current_server
    global difficulty
    server_name = None
    min_shares = difficulty*.40
    
    for server in servers:
        info = servers[server]
        if info['shares']< min_shares and info['lag'] == False:
            min_shares = servers[server]['shares']
            server_name = server

    if server_name == None:
        server_name = 'eligius'

    current_server = server_name
    server = servers[current_server]
    access = ServiceProxy("http://" + server['user']+ ":" + server['pass'] + "@" + server['mine_address'])
    return

def server_update():
    global servers
    if current_server == None:
        select_best_server()
        return

    if current_server not in servers:
        return

    if servers[current_server]['shares'] > difficulty * .40:
        select_best_server()
        return

def bclc_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['round_shares'])
    servers['bclc']['shares'] = round_shares
    print 'bitcoin.lc :' + str(round_shares)
    server_update()
    
def mtred_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['server']['servers']['n0']['roundshares'])
    servers['mtred']['shares'] = round_shares
    print 'mtred :' + str(round_shares)
    server_update()


def mineco_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['shares_this_round'])
    servers['mineco']['shares'] = round_shares
    print 'mineco :' + str(round_shares)
    server_update()

def bitclockers_sharesResponse(response):
    global servers
    info = json.loads(response)
    round_shares = int(info['roundshares'])
    servers['bitclockers']['shares'] = round_shares
    print 'bitclockers :' + str(round_shares)
    server_update()

def bclc_getshares():
    getPage('https://www.bitcoins.lc/stats.json').addCallback(bclc_sharesResponse)

def mtred_getshares():
    getPage('https://mtred.com/api/user/key/d91c52cfe1609f161f28a1268a2915b8').addCallback( mtred_sharesResponse )

def mineco_getshares():
    getPage('https://mineco.in/stats.json').addCallback(mineco_sharesResponse)

def bitclockers_getshares():
    getPage('https://bitclockers.com/api').addCallback(bitclockers_sharesResponse)

def update_servers():
    global servers
    bclc_getshares()
    mtred_getshares()
    bitclockers_getshares()
    mineco_getshares()
result = {'used':True, 'work':None}

def update_work(data):
    global result
    result['used'] = False
    result['work'] = data


def bitHopper_Post(request):
    print 'RPC request'
    #request.setHeader('X-Long-Polling', 'localhost:8337')
    rpc_request = json.load(request.content)
    #check if they are sending a valid message
    if rpc_request['method'] != "getwork":
        return json.dumps({'result':None, 'error':'Not supported', 'id':rpc_request['id']})


    #Check for data to be validated
    global servers
    global current_server
    global json_agent
    server=servers[current_server]
    data = rpc_request['params']
    data = work.jsonrpc_getwork(json_agent, server, data)
    data.addCallback(update_work)

    global result
    if result['used'] == True:
        data = None
    else:
        data = result['work']
        print data
    #server may be down
    if data == None:
        response = json.dumps({"result":None,'error':{'message':"Unable to connect to server"} ,'id':rpc_request['id']})          
    else:
        response = json.dumps({"result":data,'error':None,'id':rpc_request['id']})
    return response

class bitSite(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        return ""
        #while False:
        #    try:
        #        new_work = threads.blockingCallFromThread(reactor, getPage, LP_URL) 
        #    except:
        #        threads.blockingCallFromThread(reactor, time.sleep, 20)
        #    else:
        #        break

        #update_servers()
        #return new_work

    def render_POST(self, request):
        return bitHopper_Post(request)


    def getChild(self,name,request):
        return self


def jsonrpc_call_wrapper():
    global servers
    global current_server
    global json_agent
    server=servers[current_server]
    data = work.jsonrpc_getwork(json_agent,server)
    data.addCallback(update_work)

def main():

    site = server.Site(bitSite())
    reactor.listenTCP(8337, site)
    reactor.suggestThreadPoolSize(10)
    update_call = LoopingCall(update_servers)
    update_call.start(57)
    work_call = LoopingCall(jsonrpc_call_wrapper)
    work_call.start(53)
    reactor.run()

if __name__ == "__main__":
    main()

