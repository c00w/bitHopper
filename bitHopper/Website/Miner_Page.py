from bitHopper.Website import app, flask
import btcnet_info
import bitHopper.Configuration.Miners
    
@app.route("/miners", methods=['POST', 'GET'])
def miner():

    #Check if this is a form submission
    handle_miner_post(flask.request.form)
    
    #Get a list of currently configured miners
    miners = bitHopper.Configuration.Miners.get_miners()    
    return flask.render_template('miner.html', miners=miners) 
    
def handle_miner_post(post):
    for item in ['method','username','password']: 
        if item not in post:
            return
    
    if post['method'] == 'remove':
        bitHopper.Configuration.Miners.remove(
                post['username'], post['password'])
                
    elif post['method'] == 'add':
        bitHopper.Configuration.Miners.add(
                post['username'], post['password'])
