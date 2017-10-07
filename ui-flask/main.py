import json
import logging
import os
from datetime import datetime
import requests
import functools

from flask import Flask, request
from flask import send_from_directory, render_template
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import Gather, VoiceResponse

TWILIO_ACCOUNT = os.getenv('TWILIO_ACCOUNT')
TWILIO_AUTH = os.getenv('TWILIO_AUTH')

@functools.lru_cache(maxsize=1)
def get_twilio_client():
    return Client(TWILIO_ACCOUNT, TWILIO_AUTH)

TWILIO_FROM_PHONE = os.getenv('TWILIO_FROM_PHONE', '+441803500679')
SMS_HISTORY = {}
MSG_STORE = {}

LOGREADER_ADDRESS = os.environ["LOG_PARSER_ADDRESS"]
LOGREADER_PORT = os.environ["LOG_PARSER_PORT"]

app = Flask(__name__)


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route("/")
@app.route('/alerts/')
def alerts():
    url = "http://{}:{}/get_all".format(LOGREADER_ADDRESS, LOGREADER_PORT)
    response = requests.get(url)
    if(response.status_code != 200):
        return render_template('alerts.html', error=True, message=response.text)
    else:
        alerts = list(response.json().values())
        return render_template('alerts.html', error=False, alerts=alerts)


@app.route('/alert/<id>')
def alert(id):
    url = "http://{}:{}/get_single?uuid={}".format(LOGREADER_ADDRESS, LOGREADER_PORT, id)
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


# TWILIO SMS SERVICE

@app.route('/sms', methods=['POST'])
def sms():
    msg, to, uuid = get_contact_user()
    SMS_HISTORY[to] = uuid
    message = get_twilio_client().messages.create(to=to, from_=TWILIO_FROM_PHONE, body=msg)
    call_id = voice_call()
    return json.dumps({'message': message.sid, 'call': call_id})


def get_contact_user():
    uuid, to, msg = request.form['uuid'], request.form['to'], request.form['msg']
    if to.startswith('00'):
        to = '+{}'.format(to[2:])
    return msg, to, uuid


@app.route("/sms_respond", methods=['POST'])
def sms_reply():
    body = request.form['Body']
    from_ = request.form['From']
    uuid = SMS_HISTORY.get(from_)
    app.logger.info('got response {} {} {}'.format(uuid, from_, body))

    if uuid is not None and body:
        msg, to, uuid = get_contact_user()
        requests.post('http://localhost:8888', data={'uuid': uuid,
                                                     "old_state": 'to_acknowledge',
                                                     "new_state": 'in_progress'})

        resp = MessagingResponse()
        resp.message('{} ACCEPTED'.format(uuid))
        return str(resp)

    return None


@app.route("/voice_respond", methods=['POST'])
def voice_call():
    msg, to, uuid = get_contact_user()
    MSG_STORE[uuid, to] = msg
    call = get_twilio_client().calls.create(
        to=to,
        from_=TWILIO_FROM_PHONE,
        url="{}/voice_handle?uuid={}&to{}".format('https://precocial-tang-6014.dataplicity.io/', uuid, to)
    )
    return call.sid


@app.route("/voice_handle", methods=['GET'])
def voice_handle(uuid, to):
    msg = MSG_STORE[uuid, to]
    resp = VoiceResponse()

    if 'Digits' in request.values:
        choice = request.values['Digits']
        if choice == '1':
            resp.say('Alert accepted!')
            return str(resp)
        elif choice == '2':
            resp.say('Try again!')
            return str(resp)
        else:
            # If the caller didn't choose 1 or 2, apologize and ask them again
            resp.say("Sorry, I don't understand that choice.")
    gather = Gather(num_digits=1)
    gather.say(msg)
    resp.append(gather)
    resp.redirect('/voice')
    return str(resp)


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request. {}'.format(e))
    return 'An internal error occurred.', 500


if __name__ == "__main__":
    app.run()
