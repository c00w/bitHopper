#License#
#bitHopper by Colin Rice is licensed under a Creative Commons 
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json
import base64
import traceback

import eventlet
httplib2 = eventlet.import_patched('httplib20_7_1')
from eventlet import pools

import webob

class Work():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.i = 0
        self.httppool = pools.Pool()
        self.httppool.create = httplib2.Http

        
        self.httppool_lp = pools.Pool()
        self.httppool_lp.create = lambda: httplib2.Http(timeout=60*30)

    def jsonrpc_lpcall(self, server, url, lp):
        try:
            self.i += 1
            request = json.dumps({'method':'getwork', 'params':[], 'id':self.i}, ensure_ascii = True)
            pool = self.bitHopper.pool.servers[server]
            header = {'Authorization':"Basic " +base64.b64encode(pool['user']+ ":" + pool['pass']), 'User-Agent': 'poclbm/20110709', 'Content-Type': 'application/json' }
            with self.httppool_lp.item() as http:
                try:
                    resp, content = http.request( url, 'GET', headers=header, body=request)
                except Exception, e:
                    self.bitHopper.log_dbg('Error with an http request')
                    self.bitHopper.log_dbg(e)
                    resp = {}
                    content = None
            lp.receive(content, server)
            return None
        except Exception, e:
            self.bitHopper.log_dbg('Error in lpcall work.py')
            self.bitHopper.log_dbg(e)
            lp.receive(None, server)
            return None

    def get(self, url):
        "A utility method for getting webpages"
        header = {'User-Agent':'Mozilla/5.0 (Windows; U; MSIE 9.0; WIndows NT 9.0; en-US))'}
        with self.httppool.item() as http:
            try:
                resp, content = http.request( url, 'GET', headers=header)
            except Exception, e:
                self.bitHopper.log_dbg('Error with an http request')
                self.bitHopper.log_dbg(e)
                resp = {}
                content = ""
                
        return content

    def jsonrpc_call(self, server, data):
        try:
            request = json.dumps({'method':'getwork', 'params':data, 'id':self.i}, ensure_ascii = True)
            self.i += 1
            
            info = self.bitHopper.pool.get_entry(server)
            header = {'Authorization':"Basic " +base64.b64encode(info['user']+ ":" + info['pass']), 'User-Agent': 'poclbm/20110709','Content-Type': 'application/json' }
            url = "http://" + info['mine_address']
            with self.httppool.item() as http:
                try:
                    resp, content = http.request( url, 'POST', headers=header, body=request)
                except Exception, e:
                    self.bitHopper.log_dbg('Error with an http request')
                    self.bitHopper.log_dbg(e)
                    resp = {}
                    content = ""

            #Check for long polling header
            lp = self.bitHopper.lp
            if lp.check_lp(server):
                #bitHopper.log_msg('Inside LP check')
                for k,v in resp.items():
                    if k.lower() == 'x-long-polling':
                        lp.set_lp(v,server)
                        break
        except Exception, e:
            self.bitHopper.log_dbg('Caught, jsonrpc_call insides')
            self.bitHopper.log_dbg(e)
            traceback.print_exc()
            return None

        try:
            message = json.loads(content)
            value =  message['result']
            return value
        except Exception, e:
            self.bitHopper.log_dbg( "Error in json decoding, Server probably down")
            self.bitHopper.log_dbg(server)
            self.bitHopper.log_dbg(content)
            return None

    def jsonrpc_getwork(self, server, data, request):
        tries = 0
        work = None
        while work == None:
            tries += 1
            try:
                if tries > 4:
                    eventlet.sleep(0.5)
                work = self.jsonrpc_call(server,data)
            except Exception, e:
                self.bitHopper.log_dbg( 'caught, inner jsonrpc_call loop')
                self.bitHopper.log_dbg(server)
                self.bitHopper.log_dbg(e)
                work = None
            if data == [] and tries > 2:
                server = self.bitHopper.get_new_server(server)
            elif tries > 2:
                self.bitHopper.get_new_server(server)
        return work

    def handle(self, env, start_request):
        
        start_request('200 OK', [("Content-type", "text/json"), 
                                 ('X-Long-Polling', '/LP')])

        request = webob.Request(env)
        rpc_request = json.loads(request.body)

        #check if they are sending a valid message
        if rpc_request['method'] != "getwork":
            return

        data = rpc_request['params']
        j_id = rpc_request['id']

        if data != []:
            server = self.bitHopper.getwork_store.get_server(data[0][72:136])
        if data == [] or server == None:
            server = self.bitHopper.pool.get_current()

        work = self.jsonrpc_getwork(server, data, request)

        response = json.dumps({"result":work, 'error':None, 'id':j_id})        

        #some reject callbacks and merkle root stores
        if str(work) == 'False':
            data = env.get('HTTP_AUTHORIZATION').split(None, 1)[1]
            username, password = data.decode('base64').split(':', 1)
            self.bitHopper.reject_callback(server, data, username, password)
        elif str(work) != 'True':
            merkle_root = work["data"][72:136]
            self.bitHopper.getwork_store.add(server,merkle_root)

        #Fancy display methods
        if self.bitHopper.options.debug:
            self.bitHopper.log_msg('RPC request ' + str(data) + " submitted to " + server)
        elif data == []:
            self.bitHopper.log_msg('RPC request [' + rpc_request['method'] + "] submitted to " + server)
        else:
            self.bitHopper.log_msg('RPC request [' + str(data[0][155:163]) + "] submitted to " + server)

        if data != []:
            data = env.get('HTTP_AUTHORIZATION').split(None, 1)[1]
            username, password = data.decode('base64').split(':', 1)
            self.bitHopper.data_callback(server, data, username,password) #request.remote_password)
        return [response]

    def handle_LP(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/json')])
        
        request = webob.Request(env)
        try:
            rpc_request = json.loads(request.body)
            j_id = rpc_request['id']
        except Exception, e:
            self.bitHopper.log_dbg('Error in json handle_LP')
        
        value = self.bitHopper.lp_callback.read()

        response = json.dumps({"result":value, 'error':None, 'id':j_id})

        return [response]
