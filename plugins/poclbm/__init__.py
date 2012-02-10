#!/usr/bin/python
#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

from BitcoinMiner import *
from optparse import OptionGroup, OptionParser
from time import sleep
import HttpTransport
import pyopencl as cl
import socket
import gevent

def main(bitHopper):
    try:
        return poclbmMiner(bitHopper)
    except Exception, e:
        print e

class poclbmSite():
    def __init__(self, Miner):
        self.Miner = Miner
        self.site_names = ['/miners', '/miner']

    def handle(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/html')])

        #Handle Possible Post values
        #self.handle_POST(webob.Request(env))

        return ["Not implemented yet!!!!!"]

    def handle_POST(self, request):
        for v in request.POST:
            if "role" in v:
                try:
                    server = v.split('-')[1]
                    self.bh.pool.get_entry(server)['role'] = request.POST[v]
                    self.bh.pool.get_entry(server)['refresh_time'] = 60
                    if request.POST[v] in ['mine','info']:
                        self.bh.pool.update_api_server(server)

                except Exception, e:
                    self.bh.log_msg('Incorrect http post request role')
                    self.bh.log_msg(e)

class poclbmMiner():
    def __init__(self, bh):
        self.miners = []
        self.bitHopper = bh
        self.bitHopper.website.sites.append(poclbmSite(self))        
    #Taken from poclbm's public domain frontend.
    def new_miner(self, option_string):
        gevent.spawn(self._new_miner, option_string)

    def _new_miner(self, option_string):

        # Socket wrapper to enable socket.TCP_NODELAY and KEEPALIVE
        realsocket = socket.socket
        def socketwrap(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
            sockobj = realsocket(family, type, proto)
            sockobj.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sockobj.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            return sockobj
        socket.socket = socketwrap

        VERSION = '20110709'

        usage = "usage: %prog [OPTION]... SERVER[#tag]...\nSERVER is one or more [http[s]://]user:pass@host:port          (required)\n[#tag] is a per SERVER user friendly name displayed in stats   (optional)"
        parser = OptionParser(version=VERSION, usage=usage)
        parser.add_option('--verbose',        dest='verbose',    action='store_true', help='verbose output, suitable for redirection to log file')
        parser.add_option('-q', '--quiet',    dest='quiet',      action='store_true', help='suppress all output except hash rate display')

        group = OptionGroup(parser, "Miner Options")
        group.add_option('-r', '--rate',      dest='rate',       default=1,           help='hash rate display interval in seconds, default=1 (60 with --verbose)', type='float')
        group.add_option('-e', '--estimate',  dest='estimate',   default=900,         help='estimated rate time window in seconds, default 900 (15 minutes)', type='int')
        group.add_option('-a', '--askrate',   dest='askrate',    default=5,           help='how many seconds between getwork requests, default 5, max 10', type='int')
        group.add_option('-t', '--tolerance', dest='tolerance',  default=2,           help='use fallback pool only after N consecutive connection errors, default 2', type='int')
        group.add_option('-b', '--failback',  dest='failback',   default=10,          help='attempt to fail back to the primary pool every N getworks, default 10', type='int')
        parser.add_option('--no-server-failbacks', dest='nsf',   action='store_true', help='disable using failback hosts provided by server')
        parser.add_option_group(group)

        group = OptionGroup(parser, "Kernel Options")
        group.add_option('-p', '--platform', dest='platform',   default=-1,          help='use platform by id', type='int')
        group.add_option('-d', '--device',   dest='device',     default=-1,          help='use device by id, by default asks for device', type='int')
        group.add_option('-w', '--worksize', dest='worksize',   default=-1,          help='work group size, default is maximum returned by opencl', type='int')
        group.add_option('-f', '--frames',   dest='frames',     default=30,          help='will try to bring single kernel execution to 1/frames seconds, default=30, increase this for less desktop lag', type='int')
        group.add_option('-s', '--sleep',    dest='frameSleep', default=0,           help='sleep per frame in seconds, default 0', type='float')
        group.add_option('-v', '--vectors',  dest='vectors',    action='store_true', help='use vectors')
        parser.add_option_group(group)

        (options, options.servers) = parser.parse_args(option_string.split())


        platforms = cl.get_platforms()

        if options.platform >= len(platforms) or (options.platform == -1 and len(platforms) > 1):
            print 'Wrong platform or more than one OpenCL platforms found, use --platform to select one of the following\n'
            for i in xrange(len(platforms)):
                print '[%d]\t%s' % (i, platforms[i].name)
            sys.exit()

        if options.platform == -1:
            options.platform = 0

        devices = platforms[options.platform].get_devices()
        if (options.device == -1 or options.device >= len(devices)):
            #print 'No device specified or device not found, use -d to specify one of the following\n'
            #for i in xrange(len(devices)):
                #print '[%d]\t%s' % (i, devices[i].name)
            return

        miner = None
        try:
            miner = BitcoinMiner(devices[options.device], options, VERSION, HttpTransport.HttpTransport)
            self.miners.append({'object':miner, 'device':options.device, 'string':option_string})
            miner.start()
        except KeyboardInterrupt:
            print '\nbye'
        finally:
            if miner: miner.stop()
        sleep(1.1)
