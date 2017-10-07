import logging

import os
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

TWILIO_ACCOUNT = os.getenv('TWILIO_ACCOUNT')
TWILIO_AUTH = os.getenv('TWILIO_AUTH')
TWILIO_CLIENT = Client(TWILIO_ACCOUNT, TWILIO_AUTH)
TWILIO_FROM_PHONE = os.getenv('TWILIO_FROM_PHONE', '+441803500679')

SMS_HISTORY = {}


@app.route('/')
def hello():
    return 'SmartAlert'


@app.route('/sms/<uuid>/<to>/<msg>')
def sms(uuid, to, msg):
    SMS_HISTORY[to] = uuid
    message = TWILIO_CLIENT.messages.create(to=to, from_=sms, body=msg)
    return message.sid


@app.route("/sms_respond", methods=['GET', 'POST'])
def sms_reply():
    body = request.form['Body']
    from_ = request.form['From']
    uuid = SMS_HISTORY[from_]

    logging.info('{} {} {}'.format(uuid, from_, body))

    resp = MessagingResponse()
    resp.message('{} ACCEPT'.format(uuid))
    return str(resp)


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request. {}'.format(e))
    return 'An internal error occurred.', 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)
