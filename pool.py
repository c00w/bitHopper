#!/bin/python

import json
from jsonrpc import ServiceProxy

from twisted.web import server, resource
from twisted.internet import reactor

class Simple(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        return "<html>Hello, world!</html>"

    def getChild(self,name,request):
        return self

def jsonrpc_getwork():
    access = ServiceProxy("http://securerpc:bitcoin4access@127.0.0.1:8332")
    v = access.getwork()
    print v
    return v


def main():

    site = server.Site(Simple())
    reactor.listenTCP(8337, site)
    reactor.run()

if __name__ == "__main__":
    main()

