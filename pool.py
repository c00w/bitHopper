#!/bin/python

from jsonrpc import ServiceProxy

access = ServiceProxy("http://securerpc:bitcoin4access@127.0.0.1:8332")
print access.getinfo()
print access.listrecievedbyaddress(1)
