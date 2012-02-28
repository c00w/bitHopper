#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

import json, base64, traceback, logging

import gevent
import httplib2
from gevent import pool
import socket

from peak.util import plugins

import ResourcePool
# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

import webob

class Work():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.workers = self.bitHopper.workers
        self.i = 0
        self.http_pool = ResourcePool.Pool(self._make_http)
        
    def _make_http(self, timeout = None):
        try:
            configured_timeout = self.bitHopper.config.getfloat('main','work_request_timeout')
        except:
            configured_timeout = 5
        if not timeout:
            timeout = configured_timeout
            
        return httplib2.Http(disable_ssl_certificate_validation=True, timeout=timeout)

    def jsonrpc_lpcall(self, server, url, lp):
        try:
            #self.i += 1
            #request = json.dumps({'method':'getwork', 'params':[], 'id':self.i}, ensure_ascii = True)
            user, passw, error = self.workers.get_worker(server)
            if error:
                return None
            header = {'Authorization':"Basic " +base64.b64encode(user+ ":" + passw).replace('\n',''), 'user-agent': 'poclbm/20110709', 'Content-Type': 'application/json', 'connection': 'keep-alive'}
            with self.http_pool(url, timeout=15*60) as http:
                try:
                    resp, content = http.request( url, 'GET', headers=header)#, body=request)[1] # Returns response dict and content str
                except Exception, e:
                    logging.debug('Error with a jsonrpc_lpcall http request')
                    logging.debug(e)
                    content = None
            lp.receive(content, server, (user, passw))
            return
        except Exception, e:
            logging.debug('Error in lpcall work.py')
            logging.debug(e)
            lp.receive(None, server, None)

    def get(self, url, useragent=None):
        """A utility method for getting webpages"""
        if useragent == None:
            try:
                useragent = self.bitHopper.config.get('main', 'work_user_agent')
            except:
                useragent = 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)'
                pass
        #logging.debug('user-agent: ' + useragent + ' for ' + str(url) )
        header = {'user-agent':useragent}
        with self.http_pool(url) as http:
            try:
                content = http.request( url, 'GET', headers=header)[1] # Returns response dict and content str
            except Exception, e:
                logging.debug('Error with a work.get() http request: ' + str(e))
                #traceback.print_exc()
                content = ""
        return content

    def jsonrpc_call(self, server, data, client_header={}, username = None, password = None):
        try:
            request = json.dumps({'method':'getwork', 'params':data, 'id':self.i}, ensure_ascii = True)
            self.i += 1
            
            info = self.bitHopper.pool.get_entry(server)
            if username and password:
                user = username
                passw = password
            else:
                user, passw, error = self.workers.get_worker(server)
                if error:
                    logging.error(error)
                    return None, None, None
            
            header = {'Authorization':"Basic " +base64.b64encode(user + ":" + passw).replace('\n',''), 'connection': 'keep-alive'}
            header['user-agent'] = 'poclbm/20110709'
            for k,v in client_header.items():
                #Ugly hack to deal with httplib trying to be smart and supplying its own user agent.
                if k.lower() in [ 'user-agent', 'user_agent']:
                    header['user-agent'] = v
                if k.lower() in ['x-mining-extensions', 'x-mining-hashrate']:
                    header[k] = v

            url = "http://" + info['mine_address']
            with self.http_pool(url) as http:
                try:
                    resp, content = http.request( url, 'POST', headers=header, body=request)
                except Exception, e:
                    logging.debug('jsonrpc_call http error: ' + str(e))
                    return None, None, None

            #Check for long polling header
            lp = self.bitHopper.lp
            if lp.check_lp(server):
                #bitHopper.log_msg('Inside LP check')
                for k,v in resp.items():
                    if k.lower() == 'x-long-polling':
                        lp.set_lp(v,server)
                        break
        except Exception, e:
            logging.debug('jsonrpc_call error: ' + str(e))
            if self.bitHopper.options.debug:
                traceback.print_exc()
            return None, None, None

        try:
            message = json.loads(content)
            value =  message['result']
            return value, resp, (user, passw)
        except Exception, e:
            logging.debug( "Error in json decoding, Server probably down")
            logging.debug(server)
            logging.debug(content)
            return None, None, None

    def jsonrpc_getwork(self, server, data,  headers={}, username = None, password = None):
        tries = 0
        work = None
        auth = None
        while work == None:
            if data == [] and tries > 1:
                server = self.bitHopper.get_new_server(server)
            elif data != [] and tries > 1:
                self.bitHopper.get_new_server(server)
            if tries >2:
                return None, {}, 'No Server', None
            tries += 1
            try:
                work, server_headers, auth = self.jsonrpc_call(server, data, headers, username, password)
            except Exception, e:
                logging.debug( 'caught, inner jsonrpc_call loop')
                logging.debug(server)
                logging.debug(e)
                work = None
        return work, server_headers, server, auth

    def handle(self, env, start_request):

        request = webob.Request(env)
        try:
            rpc_request = json.loads(request.body)
        except:
            start_request('200 OK', {})
            return ['Go to /stats']

        client_headers = {}
        for header in env:
            if header[0:5] in 'HTTP_':
                client_headers[header[5:].replace('_','-')] = env[header]

        data = rpc_request['params']
        j_id = rpc_request['id']

        #check if they are sending a valid message
        if rpc_request['method'] != "getwork":
            start_request('200 OK', {})
            response = json.dumps({"result":None, 'error':{'message':'Invalid method'}, 'id':j_id})
            return [response]

        if data != []:
            server, auth = self.bitHopper.getwork_store.get_server(data[0][72:136])
            if not auth:
                start_request('200 OK', {})
                return json.dumps({"result":None, 'error':{'message':'Root not found'}, 'id':j_id})
            serv_user, serv_pass = auth
        if data == [] or server == None:
            server = self.bitHopper.pool.get_work_server()
            serv_user, serv_pass, err = self.workers.get_worker(server)

        auth_data = env.get('HTTP_AUTHORIZATION').split(None, 1)[1]
        username, password = auth_data.decode('base64').split(':', 1)

        work, server_headers, server, auth  = self.jsonrpc_getwork(server, data, client_headers, serv_user, serv_pass)

        to_delete = []
        for header in server_headers:
            if header.lower() not in ['x-roll-ntime','x-reject-reason']:
                to_delete.append(header)
        for item in to_delete:
            del server_headers[item]  

        server_headers['X-Long-Polling'] = '/LP'

        start_request('200 OK', server_headers.items())

        if work == None:
            response = json.dumps({"result":None, 'error':{'message':'Cannot get work unit'}, 'id':j_id})
        else:
            response = json.dumps({"result":work, 'error':None, 'id':j_id}) 
            gevent.spawn(self.handle_store, work, server, data, username, password, rpc_request, auth)
        return [response]       

    def handle_store(self, work, server, data, username, password, rpc_request, auth):

        #some reject callbacks and merkle root stores
        if str(work).lower() == 'false':
            self.bitHopper.reject_callback(server, data, username, password)
        elif str(work).lower() != 'true':
            merkle_root = work["data"][72:136]
            self.bitHopper.getwork_store.add(server,merkle_root, auth)

        #Fancy display methods
        hook = plugins.Hook('work.rpc.request')
        hook.notify(rpc_request, data, server)

        if data != []:
            self.bitHopper.data_callback(server, data, username,password) #request.remote_password)

    def handle_LP(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/json')])
        
        request = webob.Request(env)
        j_id = None
        try:
            rpc_request = json.loads(request.body)
            j_id = rpc_request['id']

        except Exception, e:
            logging.debug('Error in json handle_LP')
            logging.debug(e)
            if not j_id:
                j_id = 1
        
        value = self.bitHopper.lp_callback.read()

        try:
            data = env.get('HTTP_AUTHORIZATION').split(None, 1)[1]
            username = data.decode('base64').split(':', 1)[0] # Returns ['username', 'password']
        except Exception,e:
            username = ''

        logging.info('LP Callback for miner: '+ username)

        response = json.dumps({"result":value, 'error':None, 'id':j_id})

        return [response]
