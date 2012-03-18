#!/usr/bin/python
#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

import logging

from peak.util import plugins

class RPCWorkLog():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        hook = plugins.Hook('work.rpc.request')
        hook.register(self.rpcWorkReport)
                            
    def rpcWorkReport(self, rpc_request, data, server):
        if self.bitHopper.options.debug:
            logging.info('RPC request ' + str(data) + " submitted to " + server)
        elif data == []:
            logging.info('RPC request [' + rpc_request['method'] + "] submitted to " + server)
        else:
            logging.info('RPC request [' + data[0][155:163] + "] submitted to " + server)
