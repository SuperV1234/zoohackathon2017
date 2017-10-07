from datetime import datetime
import requests
import os

from flask import Flask, send_from_directory, render_template

app = Flask(__name__)


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route("/")
@app.route('/alerts/')
def alerts():
    address = os.environ["LOG_PARSER_ADDRESS"]
    port = os.environ["LOG_PARSER_PORT"]
    url = "http://{}:{}/get_all".format(address, port)
    response = requests.get(url)
    if(response.status_code != 200):
        return render_template('alerts.html', error=True, message=response.text)
    else:
        alerts = list(response.json().values())
        return render_template('alerts.html', error=False, alerts=alerts)


@app.route('/alert/<id>')
def alert(id):
    address = os.environ["LOG_PARSER_ADDRESS"]
    port = os.environ["LOG_PARSER_PORT"]
    url = "http://{}:{}/get_single?uuid={}".format(address, port, id)
    response = requests.get(url)
    if(response.status_code != 200):
        return render_template('alerts.html', error=True, message=response.text)
    else:
        return render_template('alert.html', error=False, alert=response.json())


@app.route('/dashboard/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/teams/')
def teams():
    return render_template('teams.html')


@app.route('/team/<name>')
def team(name):
    return render_template('team.html', name=name)


@app.route('/rangers/')
def rangers():
    return render_template('rangers.html')


@app.route('/ranger/<name>')
def ranger(name):
    return render_template('ranger.html', name=name)


if __name__ == "__main__":
    app.run()
