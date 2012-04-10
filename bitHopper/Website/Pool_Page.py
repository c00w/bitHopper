from bitHopper.Website import app, flask
import bitHopper.Tracking.Tracking

@app.route("/pool", methods=['POST', 'GET'])
def worker():

    pools = bitHopper.Tracking.Tracking.build_dict()
        
    return flask.render_template('pool.html', pools = pools)
