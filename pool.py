#!/bin/python

import json
from jsonrpc import ServiceProxy

from twisted.web import server, resource
from twisted.internet import reactor

access = ServiceProxy("http://19ErX2nDvNQgazXweD1pKrjbBLKQQDM5RY:x@mining.eligius.st:8337")

def jsonrpc_getwork(data):
    global access
    if data == None or data == []:
        v = access.getwork()
    else: v = access.getwork(data)
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
    reactor.run()

if __name__ == "__main__":
    main()

