"""
A fake pool that only serves one getwork, meant for local testing
"""
import gevent.pywsgi
import os, logging, json

def handle_getwork():
    response = {"id":1,"error":None,"result":{"midstate":"5fa3febd7c47f69762101eb58f7e07f86414f6cddab264ea29e979e93a681af3","target":"ffffffffffffffffffffffffffffffffffffffffffffffffffffffff00000000","data":"0000000141eb2ea2dff39b792c3c4112408b930de8fb7e3aef8a75f400000709000000001d716842411d0488da0d1ccd34e8f3e7d5f0682632efec00b80c7e3f84e175854fb7bead1a09ae0200000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000","hash1":"00000000000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000010000"}}
    return json.dumps(response) 
    
def handle_submit():
    response = {'result':True, 'id':1, 'error':None}
    return json.dumps(response)

def read_input(env):
    inp = env['wsgi.input']
    r = ""
    while True:
        a = inp.read()
        if a == None or len(a) == 0:
            break
        r += a
    return r

def initialize():
    log = open(os.devnull, 'wb')
    server = gevent.pywsgi.WSGIServer(('127.0.0.1', 8338), serve, log=log)
    gevent.spawn(server.serve_forever)
        
def serve(env, start_response):
    start_response('200 OK', [])
    
    body = read_input(env)
    body = json.loads(body)
    
    if body['params'] != []:
        return handle_submit()
    return handle_getwork()

    
