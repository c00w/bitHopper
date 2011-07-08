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

from zope.interface import implements

from twisted.web import server, resource
from twisted.web.client import getPage, Agent
from twisted.web.iweb import IBodyProducer
from twisted.web.http_headers import Headers
from twisted.internet import reactor, threads, defer
from twisted.internet.defer import succeed, Deferred
from twisted.internet.task import LoopingCall
from twisted.internet.protocol import Protocol

#SET THESE
bclc_user  = "FSkyvM"
bclc_pass = "xndzEU"
mtred_user = 'scarium'
mtred_pass = 'x'
eligius_address = '1AofHmwVef5QkamCW6KqiD4cRqEcq5U7hZ'


LP_URL = 'non existant adress'

difficulty = 1563027.996116
access = None
#access = ServiceProxy("http://19ErX2nDvNQgazXweD1pKrjbBLKQQDM5RY:x@mining.eligius.st:8337")
servers = {
        'bclc':{'time':time.time(), 'shares':0, 'name':'bitcoins.lc', 'mine_address':'bitcoins.lc:8080', 'user':bclc_user, 'pass':bclc_pass, 'lag':False, 'LP':None},
        'mtred':{'time':time.time(), 'shares':0, 'name':'mtred',  'mine_address':'mtred.com:8337', 'user':mtred_user, 'pass':mtred_pass, 'lag':False, 'LP':None},
        'eligius':{'time':time.time(), 'shares':difficulty*.41, 'name':'eligius', 'mine_address':'mining.eligius.st:8337', 'user':eligius_address, 'pass':'x', 'lag':False, 'LP':None}
        }
current_server = 'mtred'

i = 1

json_agent = Agent(reactor)

work = {'used':True, 'unit':None}

class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)
    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class WorkProtocol(Protocol):

    def __init__(self, finished):
        self.data = ""
        self.finished = finished
        print "initialized"
    
    def dataRecieved(self, data):
        self.data += data
        print "data recieved"

    def connectionLost(self, reason):
        global work
        print self.data

        try:
            data = json.loads(self.data)['result']
        except Exception as e:
            print "Error " + str(e)

        print work
        self.finished.callback(None)

def select_best_server():

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

def bclc_getshares():
    getPage('https://www.bitcoins.lc/stats.json').addCallback(bclc_sharesResponse)

def mtred_getshares():
    getPage('https://mtred.com/api/user/key/d91c52cfe1609f161f28a1268a2915b8').addCallback( mtred_sharesResponse )

def update_servers():
    global servers
    bclc_getshares()
    mtred_getshares()

def jsonrpc_update(result):
    print 'Response Recieved'
    finish = Deferred()
    result.deliverBody(WorkProtocol(finish))
    print 'Body Delivered'
    return finish

def errorback(error):
    print error.getErrorMessage()
    #print dir(error)
    #print error.printDetailedTraceback()
    error.throwExceptionIntoGenerator

def jsonrpc_call(data = []):
    global i
    global work
    request = json.dumps({'method':'getwork', 'params':data, 'id':i}, ensure_ascii = True)
    i = i +1
    global json_agent
    global servers
    global current_server

    server = servers[current_server]
    
    header = {'Authorization':["Basic " +base64.b64encode(server['user']+ ":" + server['pass'])]}

    d = json_agent.request('POST', "http://" + server['mine_address'], Headers(header), StringProducer(request))
    d.addCallback(jsonrpc_update)
    d.addErrback(errorback)

    return work
    
def jsonrpc_call_wrapper():
    jsonrpc_call()

def jsonrpc_getwork(data = []):
    global access
    global servers
    global current_server
    
    print 'Data sent:' + str(data)
    if current_server == None:
        server_update()
        select_best_server()
        
    server = servers[current_server]
    while True:
        try:
            work = jsonrpc_call(data)
            print work
            if work['used'] :
                time.sleep(0.5)
        except socket.error, e:
            print e
            servers[current_server]['lag'] = True
            select_best_server()
        else:    
            servers[current_server]['lag'] = False
            print "Pulled From " + current_server + ", Current shares " + str(servers[current_server]['shares'])
            return work



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
        print 'RPC request'
        #request.setHeader('X-Long-Polling', 'localhost:8337')
        rpc_request = json.load(request.content)
        #check if they are sending a valid message
        if rpc_request['method'] != "getwork":
            return json.dumps({'result':None, 'error':'Not supported', 'id':rpc_request['id']})


        #Check for data to be validated
        data = rpc_request['params']
        data = jsonrpc_getwork(data)['unit']
        if work['unit'] == None:
            response = json.dumps({"result":'','error':{'message':"Unable to connect to server"} ,'id':rpc_request['id']})          
        else:
            response = json.dumps({"result":data,'error':None,'id':rpc_request['id']})
        return response


    def getChild(self,name,request):
        return self


def main():

    site = server.Site(bitSite())
    reactor.listenTCP(8337, site)
    update_call = LoopingCall(update_servers)
    update_call.start(57)
    work_call = LoopingCall(jsonrpc_call_wrapper)
    work_call.start(53)
    reactor.run()

if __name__ == "__main__":
    main()

