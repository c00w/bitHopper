"""
A fake pool that only serves one getwork, meant for local testing
"""
import gevent.pywsgi
import os, logging, json

def handle_getwork():
    response = {'result':{'data':'F'* 168}, 'id':1, 'error':None}
    return json.dumps(response) 
    
def handle_submit():
    response = {'result':'true', 'id':1, 'error':None}
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
    print body
    if body['params'] != []:
        return handle_submit()
    return handle_getwork()
    logging.info('Fake Work Server')

    
