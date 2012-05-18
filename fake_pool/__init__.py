"""
A fake pool that only serves one getwork, meant for local testing
"""
import gevent.pywsgi
import os, logging, json

def initialize():
    log = open(os.devnull, 'wb')
    server = gevent.pywsgi.WSGIServer(('127.0.0.1', 8338), serve, log=log)
    gevent.spawn(server.serve_forever)
        
def serve(env, start_response):
    start_response('200 OK', [])
    logging.info('Fake Work Server')

    response = {'result':{'data':'F'* 168}, 'id':1, 'error':None}
    return json.dumps(response)
