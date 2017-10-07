from datetime import datetime

from flask import Flask, send_from_directory, render_template

app = Flask(__name__)


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route("/")
@app.route('/alerts/')
def alerts():
    alert = {
        "type": "Ground Sensor",
        "time": datetime.now(),
        "label": "Elephant",
        "id": "1234567",
        "status": "warn"
    }
    return render_template('alerts.html', alerts=[alert, alert, alert])


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


@app.route('/alert/<name>')
def alert(name):
    return render_template('alert.html', name=name)


if __name__ == "__main__":
    app.run()
