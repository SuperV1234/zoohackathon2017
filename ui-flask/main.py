import functools
import json
import logging
import os
from urllib.parse import quote

import requests
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
    try:
        response = requests.get(url)
    except requests.exceptions.ConnectionError as e:
        return render_template('alerts.html', error=True, message=e.response.text)
    else:
        alerts = list(response.json().values())
        for alert in alerts:
            if "INTRUDER" in alert["label"]:
                alert["isIntruder"] = True
            if "ARMED" in alert["label"]:
                alert["isArmed"] = True
            if "SENSOR" in alert["name"]:
                alert["isSensor"] = True
        return render_template('alerts.html', error=False, alerts=alerts, teams=[1,2,3,4])


@app.route('/alert/<id>')
def alert(id):
    url = "http://{}:{}/get_single?uuid={}".format(LOGREADER_ADDRESS, LOGREADER_PORT, id)
    try:
        response = requests.get(url)
    except requests.exceptions.ConnectionError as e:
        return render_template('alerts.html', error=True, message=e.response.text)
    else:
        return render_template('alert.html', error=False, alert=response.json())


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
    lone1 =  {'name': 'John'}
    texas1 = {'name': 'Jack'}
    power1 = {'name': 'Sophie'}
    lone2 =  {'name': 'Lone'}
    texas2 = {'name': 'Texas'}
    power2 = {'name': 'Power'}
    return render_template('rangers.html', rangers=[lone, texas, power,lone1, texas1, power1,lone2, texas2, power2])


@app.route('/ranger/<name>')
def ranger(name):
    return render_template('ranger.html', name=name)


@app.route('/')
def hello():
    return 'SmartAlert'


# TWILIO SMS SERVICE

@app.route('/sms', methods=['POST'])
def sms():
    msg, to, uuid = get_contact_user()
    SMS_HISTORY[to] = uuid
    body = '''{}
TEXT 1 to ACCEPT!'''.format(msg)
    message = get_twilio_client().messages.create(to=to, from_=TWILIO_FROM_PHONE, body=body)
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
        requests.post('http://localhost:8888', data={'uuid': uuid,
                                                     "old_state": 'to_acknowledge',
                                                     "new_state": 'in_progress'})

        resp = MessagingResponse()
        resp.message(accept_alert(uuid))
        return str(resp)

    return None


def accept_alert(uuid):
    return '{} ACCEPTED'.format(uuid)


@app.route("/voice_respond", methods=['POST'])
def voice_call():
    msg, to, uuid = get_contact_user()
    MSG_STORE[uuid, to] = msg
    call = get_twilio_client().calls.create(
        to=to,
        from_=TWILIO_FROM_PHONE,
        url="{}/voice_handle?uuid={}&to={}".format('http://precocial-tang-6014.dataplicity.io',
                                                   quote(uuid),
                                                   quote(to))
    )
    return call.sid


@app.route("/voice_handle", methods=['GET', 'POST'])
def voice_handle():
    uuid, to = request.args.get('uuid'), request.args.get('to')
    resp = VoiceResponse()
    if 'Digits' in request.values:
        choice = request.values['Digits']
        if choice == '1':
            resp.say('Alert accepted!')
            get_twilio_client().messages.create(to=to, from_=TWILIO_FROM_PHONE, body=accept_alert(uuid))
            return str(resp)
        elif choice == '2':
            resp.say('Try again!')
            return str(resp)
        else:
            # If the caller didn't choose 1 or 2, apologize and ask them again
            resp.say("Sorry, I don't understand that choice.")
    gather = Gather(num_digits=1)
    body = '''{}, press 1 to accept!'''.format(MSG_STORE[uuid, to])
    gather.say(body)
    resp.append(gather)
    resp.redirect('/voice_respond', method='POST')
    return str(resp)


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request. {}'.format(e))
    return 'An internal error occurred.', 500


if __name__ == "__main__":
    app.run(debug=True)
