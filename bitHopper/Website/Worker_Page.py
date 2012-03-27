from bitHopper.Website import app, flask

@app.route("/worker")
def worker():
    return flask.render_template('worker.html')
