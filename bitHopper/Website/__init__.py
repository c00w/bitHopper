import logging, json, flask, traceback, random
import bitHopper.Tracking
import bitHopper.util
import bitHopper.Network

app = flask.Flask('bitHopper', template_folder='templates', 
            static_folder = 'static')
app.Debug = False

# Set a secret key. Mainly used for CSRF. Should be random otherwise 
# no protection since no one is going to remember to change this
ascii_uppercase = 'ABCDEFHIJKLMNOPQRXTUVWXYZ'
digits = '0123456789'
app.secret_key = ''.join(random.choice(ascii_uppercase + digits) for x in range(20))

@app.teardown_request
def teardown_request_wrap(exception):
    """
    Prints tracebacks and handles bugs
    """
    if exception:
        logging.error(traceback.format_exc())
        return json.dumps({"result":None, 'error':{'message':'Invalid request'}, 'id':1})
        
import Worker_Page
import Pool_Page

@app.route("/")
def frontpage():
    return flask.render_template('index.html')
