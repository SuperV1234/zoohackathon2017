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
        "id": "1234567"
    }
    return render_template('index.html', alerts=[alert, alert, alert])


@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)


if __name__ == "__main__":
    app.run()