from datetime import datetime

from flask import Flask, send_from_directory, render_template

app = Flask(__name__)


@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)


@app.route("/")
def index():
    alert = {
        "type": "Ground Sensor",
        "time": datetime.now(),
        "label": "Elephant",
        "id": "1234567",
        "status": "warn"
    }
    return render_template('index.html', alerts=[alert, alert, alert])


@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)

@app.route('/dashboard/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/teams/')
def teams():
    return render_template('teams.html')

@app.route('/team/<name>')
def team(name=None):
    return render_template('team.html', name=name)

@app.route('/rangers/')
def rangers(name=None):
    return render_template('rangers.html')

@app.route('/ranger/<name>')
def ranger(name=None):
    return render_template('ranger.html', name=name)

@app.route('/alerts/')
def alerts(name=None):
    return render_template('alerts.html')

@app.route('/alert/<name>')
def alert(name=None):
    return render_template('alert.html', name=name)



if __name__ == "__main__":
    app.run()
