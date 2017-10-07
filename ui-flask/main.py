from datetime import datetime

from flask import Flask, send_from_directory, render_template

app = Flask(__name__)


@app.route('/static/<path:path>')
def serve_static(path):
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


@app.route('/teams_or_rangers/')
def teams_or_rangers():
    return render_template('teams_or_rangers.html')


@app.route('/teams/')
def teams():
    return render_template('teams.html')


@app.route('/team/<name>')
def team(name):
    return render_template('team.html', name=name)


@app.route('/rangers/')
def rangers():
    lone =  {'name': 'Lone'} 
    texas = {'name': 'Texas'} 
    power = {'name': 'Power'} 
    return render_template('rangers.html', rangers=[lone, texas, power])


@app.route('/ranger/<name>')
def ranger(name):
    return render_template('ranger.html', name=name)


@app.route('/alerts/')
def alerts():
    return render_template('alerts.html')


@app.route('/alert/<name>')
def alert(name):
    return render_template('alert.html', name=name)


if __name__ == "__main__":
    app.run(debug=True)


