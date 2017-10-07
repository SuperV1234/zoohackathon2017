import logging
import os
from datetime import datetime

import requests
from flask import Flask, request
from flask import send_from_directory, render_template
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

TWILIO_ACCOUNT = os.getenv('TWILIO_ACCOUNT')
TWILIO_AUTH = os.getenv('TWILIO_AUTH')
TWILIO_CLIENT = Client(TWILIO_ACCOUNT, TWILIO_AUTH)
TWILIO_FROM_PHONE = os.getenv('TWILIO_FROM_PHONE', '+441803500679')
SMS_HISTORY = {}

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


@app.route('/alerts/')
def alerts():
    return render_template('alerts.html')


@app.route('/alert/<name>')
def alert(name):
    return render_template('alert.html', name=name)


@app.route('/')
def hello():
    return 'SmartAlert'


@app.route('/sms', methods=['POST'])
def sms():
    uuid, to, msg = request.form['uuid'], request.form['to'], request.form['msg']
    if to.startswith('00'):
        to = '+{}'.format(to[2:])
    SMS_HISTORY[to] = uuid
    message = TWILIO_CLIENT.messages.create(to=to, from_=TWILIO_FROM_PHONE, body=msg)
    return message.sid


@app.route("/sms_respond", methods=['POST'])
def sms_reply():
    body = request.form['Body']
    from_ = request.form['From']
    uuid = SMS_HISTORY.get(from_)
    app.logger.info('got response {} {} {}'.format(uuid, from_, body))

    if uuid is not None and body:
        requests.post('localhost:8888', data={'uuid': uuid,
                                              "old_state": 'to_acknowledge',
                                              "new_state": 'in_progress'})

        resp = MessagingResponse()
        resp.message('{} ACCEPTED'.format(uuid))
        return str(resp)

    return None


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request. {}'.format(e))
    return 'An internal error occurred.', 500


if __name__ == "__main__":
    app.run()
