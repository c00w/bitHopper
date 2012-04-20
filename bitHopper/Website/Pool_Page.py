from bitHopper.Website import app, flask
import bitHopper.Tracking.Tracking
import bitHopper.Configuration.Pools

@app.route("/pool", methods=['POST', 'GET'])
def pool():

    handle_worker_post(flask.request.form)

    pools = bitHopper.Tracking.Tracking.build_dict()
        
    return flask.render_template('pool.html', pools = pools)
    
def handle_worker_post(post):
    """
    Handles worker priority and percentage change operations
    """
    for item in ['method','server','percentage', 'priority']:
        if item not in post:
            return
    
    if post['method'] == 'set':
        pool = post['server']
        percentage = post['percentage']
        priority = post['priority']
        bitHopper.Configuration.Pools.set_percentage(
                pool, percentage)
        bitHopper.Configuration.Pools.set_priority(
                pool, priority)
                
