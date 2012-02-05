#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

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
