#!/bin/python2.7
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
from jsonrpc import ServiceProxy
import socket
import os
import base64
import exceptions

from zope.interface import implements

from twisted.web import server, resource
from twisted.web.client import getPage, Agent
from twisted.web.iweb import IBodyProducer
from twisted.web.http_headers import Headers
from twisted.internet import defer
from twisted.internet.defer import succeed, Deferred
from twisted.internet.task import LoopingCall
from twisted.internet.protocol import Protocol
i = 1

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
    
    def dataReceived(self, data):
        self.data += data

    def connectionLost(self, reason):
        self.finished.callback(self.data)

@defer.inlineCallbacks
def jsonrpc_call(agent, server,data , set_lp):
    global i
    request = json.dumps({'method':'getwork', 'params':data, 'id':i}, ensure_ascii = True)
    i = i +1
    
    header = {'Authorization':["Basic " +base64.b64encode(server['user']+ ":" + server['pass'])], 'User-Agent': ['bitHopper'],'Content-Type': ['application/json'] }
    d = agent.request('POST', "http://" + server['mine_address'], Headers(header), StringProducer(request))
    d.addErrback(lambda x: defer.returnValue(None))
    response = yield d
    header = response.headers
    print str(header)
    #Check for long polling header
    if header.hasHeader('X-Long-Polling')and set_lp(None, True):
        values = header.getRawHeaders('X-Long-Polling')
        print 'LP_HEADER: ' + str(values)
        if len(values) >0:
            set_lp(value[0])
    #Some people can't capitalize
    if header.hasHeader('x-long-polling')and set_lp(None, True):
        values = header.getRawHeaders('x-long-polling')
        print 'LP_HEADER: ' + str(values)
        if len(values) >0:
            set_lp(value[0])
    finish = Deferred()
    response.deliverBody(WorkProtocol(finish))
    finish.addErrback(lambda x: defer.returnValue(None))
    body = yield finish

    try:
        message = json.loads(body)
        value =  message['result']
        defer.returnValue(value)
    except exceptions.ValueError, e:
        print e
        defer.returnValue(None)

@defer.inlineCallbacks
def jsonrpc_getwork(agent, server, data, j_id, request, new_server, set_lp):
    work = None
    i = 0
    while work == None:
        i += 1
        if i > 10:
            new_server(server)
        work = yield jsonrpc_call(agent, server,data,set_lp)

    response = json.dumps({"result":work,'error':None,'id':j_id})

    request.write(response)
    request.finish()
