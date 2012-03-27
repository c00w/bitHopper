from bitHopper.Website import app, flask
import btcnet_info
import bitHopper.Configuration.Workers
    
@app.route("/worker", methods=['POST', 'GET'])
def worker():
    print flask.request.form
    #Check if this is a form submission
    handle_worker_post(flask.request.form)
    
    #Get a list of currently configured workers
    pools_workers = {}
    for pool in btcnet_info.get_pools():
        if not pool.name:
            continue
        pools_workers[pool.name] = bitHopper.Configuration.Workers.get_worker_from(pool.name)
        
    return flask.render_template('worker.html', pools = pools_workers)
    
def handle_worker_post(post):
    print post
    for item in ['method','username','password', 'pool']:
        if item not in post:
            print 'Not post'
            return
    
    if post['method'] == 'remove':
        print 'Removing'
        bitHopper.Configuration.Workers.remove(
                post['pool'], post['username'], post['password'])
                
    elif post['method'] == 'add':
        print 'Adding'
        bitHopper.Configuration.Workers.add(
                post['pool'], post['username'], post['password'])
        print bitHopper.Configuration.Workers.workers
