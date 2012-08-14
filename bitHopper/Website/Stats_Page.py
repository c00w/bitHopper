from bitHopper.Website import app, flask
import btcnet_info
import bitHopper.Configuration.Miners
    
@app.route("/stats", methods=['POST', 'GET'])
def stats():
    return flask.render_template('stats.html') 
