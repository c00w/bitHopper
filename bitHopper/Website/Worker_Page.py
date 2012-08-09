from bitHopper.Website import app, flask
import btcnet_info
import bitHopper.Configuration.Workers
import logging
    
@app.route("/worker", methods=['POST', 'GET'])
def worker():

    #Check if this is a form submission
    handle_worker_post(flask.request.form)
    
    #Get a list of currently configured workers
    pools_workers = {}
    for pool in btcnet_info.get_pools():
        if pool.name is None:
            logging.debug('Ignoring a Pool. If no pools apear on /worker please update your version of btcnet_info')
            continue
        pools_workers[pool.name] = bitHopper.Configuration.Workers.get_worker_from(pool.name)
        
    return flask.render_template('worker.html', pools = pools_workers)
    
def handle_worker_post(post):
    for item in ['method','username','password', 'pool']:
        if item not in post:
            return
    
    if post['method'] == 'remove':
        bitHopper.Configuration.Workers.remove(
                post['pool'], post['username'], post['password'])
                
    elif post['method'] == 'add':
        bitHopper.Configuration.Workers.add(
                post['pool'], post['username'], post['password'])
