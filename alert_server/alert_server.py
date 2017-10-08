#!/usr/bin/python3

import time
import pygtail
import argparse
import pprint
import sys
import uuid
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.web
import urllib.parse
from datetime import datetime

def cleanup_label(x):
    return x.replace('LABELLED AS', '').replace('"', '').strip()

class Alert(object):
    def __init__(self, name, sn, time, date, position, label, state, xuuid = None):
        self.uuid = uuid.uuid4() if xuuid == None else xuuid
        self.name = name
        self.sn = sn
        self.datetime = datetime.strptime(f'{date} {time}', '%d/%m/%Y %H%M UTC')
        self.position = position
        self.label = cleanup_label(label)
        self.state = state
        self.target = AlertTarget(None)
        self.code = 1234 # TODO: generate randomly, check collisions

    def __repr__(self) -> str:
        return f'''Alert[{self.uuid}]
{{
    name: {self.name}
    sn: {self.sn}
    datetime: {self.datetime}
    position: {self.position}
    label: {self.label}
    state: {self.state}
}}'''

class AlertTarget(object):
    def __init__(self, phone_number):
        self.phone_number = phone_number

    def to_json(self):
        return self.phone_number

def make_stripped_alert(alert: Alert) -> dict:
    return {
        "uuid": str(alert.uuid),
        "name": alert.name,
        "datetime": str(alert.datetime),
        "label": alert.label,
        "target": alert.target.to_json(),
        "state": alert.state,
    }

def to_uuid_dict(stripped_alerts: [dict]) -> dict:
    return {x["uuid"]: x for x in stripped_alerts}

def map_stripped_alerts(alerts: [Alert]) -> [dict]:
    return list(map(make_stripped_alert, alerts))

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def verbose_print(*args, **kwargs):
    print(*args, **kwargs)

def make_alert(data_array) -> Alert:
    return Alert(
        data_array[0], # name
        data_array[1], # sn
        data_array[2], # time
        data_array[3], # date
        data_array[4], # position
        data_array[5], # label
        "to_dispatch", # state
    )

def parse_alert_line(line) -> Alert:
    return make_alert(list(map(lambda x: x.strip(), line.split(','))))

def watch_csv_log(path):
    for line in pygtail.Pygtail(path):
        try:
            yield parse_alert_line(line)
        except:
            eprint(f"Error processing CSV line: '{line}' - skipping")

manual_mode = True
mock_target_number = "+441234567890"

def to_human_form(alert: Alert) -> str:
    a = alert
    return f'[{a.code}] {a.name} ({a.label}) at {a.datetime}'

class AlertDB(object):
    def __init__(self, http_client):
        self.alerts = []
        self.uuid_to_alert = {}
        self.http_client = http_client
        self.ctr = 0

    def dispatch(self, alert: Alert):
        global mock_target_number

        alert.target = AlertTarget("+441234567890")
        msg = f"ALERT: {to_human_form(alert)}"
        xuuid = alert.uuid;

        post_data = { 'uuid': xuuid, 'to': mock_target_number, 'msg': msg }
        body = urllib.parse.urlencode(post_data)

        def handle_response(response):
            if response.error:
                print("Error: %s" % response.error)
            else:
                print(response.body)

        self.http_client.fetch("http://localhost:80/sms", handle_response, method='POST', headers=None, body=body)

    def add_new(self, alert: Alert):
        global manual_mode

        self.alerts.append(alert)
        xuuid = alert.uuid

        verbose_print(f'[AlertDB]: Added new alert\n{alert}\n')
        self.uuid_to_alert[xuuid] = alert

        self.ctr += 1
        if self.ctr == 3:
            verbose_print(f'[AlertDB]: {xuuid} now in progress')
            alert.state = "in_progress"
            alert.target = AlertTarget(mock_target_number)
            self.ctr = 0
        elif manual_mode == True:
            verbose_print(f'[AlertDB]: {xuuid} now requires manual intervention')
            alert.state = "to_manually_dispatch"
        else:
            verbose_print(f'[AlertDB]: {xuuid} now requires ackwnowledgement')

            # TODO: implement real dispatching strategy here
            alert.state = "to_acknowledge"
            alert.target = AlertTarget(mock_target_number)
            self.dispatch(alert)

    def from_uuid(self, uuid) -> Alert:
        return self.uuid_to_alert[uuid]

    def _uuid_map(self, src) -> [Alert]:
        return list(map(self.from_uuid, src))

    def get_with_state(self, state) -> [Alert]:
        return [x for x in self.alerts if x.state == state]

    def move_between_states(self, uuid, old, new) -> bool:
        alert = self.from_uuid(uuid)
        if alert.state == old:
            alert.state = new

            if old == "to_manually_dispatch" and new == "to_acknowledge":
                # TODO: implement real dispatching strategy here
                alert.target = AlertTarget(mock_target_number)
                self.dispatch(alert)

            return True

        verbose_print(f'{uuid} not in state {old}')
        return False

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        state = self.get_argument('state', '')
        self.write(to_uuid_dict(map_stripped_alerts(self.application.alert_db.get_with_state(state))))

    def post(self):
        old_state = self.get_argument('old_state', '')
        new_state = self.get_argument('new_state', '')
        uuid_str = self.get_argument('uuid', '')
        uuid_val = uuid.UUID(uuid_str)

        verbose_print(f'[MainHandler]: received POST for {uuid_str} ({old_state} -> {new_state})')

        result = self.application.alert_db.move_between_states(uuid_val, old_state, new_state)
        self.write({"success": result})

class SingleHandler(tornado.web.RequestHandler):
    def get(self):
        xuuid = self.get_argument('uuid', '')
        self.write(make_stripped_alert(self.application.alert_db.from_uuid(uuid.UUID(xuuid))))

class AllHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(to_uuid_dict(map_stripped_alerts(self.application.alert_db.alerts)))

class ManualModeHandler(tornado.web.RequestHandler):
    def get(self):
        global manual_mode
        self.write({ "manual_mode": manual_mode })

    def post(self):
        global manual_mode
        manual_mode = self.get_argument('manual_mode', '')
        self.write({"success": True})

class MessageHandler(tornado.web.RequestHandler):
    def get(self):
        # TODO: given 4digit code, return list of messages
        pass

    def post(self):
        # TODO: given 4digit code and message, append message to alert list of message
        # TODO: if 4digit code is wrong, return success:false
        pass

class AlertApp(tornado.web.Application):
    def __init__(self):
        self.alert_db = AlertDB(tornado.httpclient.AsyncHTTPClient())

        super(AlertApp, self).__init__([
            (r"/", MainHandler),
            (r"/get_single", SingleHandler),
            (r"/get_all", AllHandler),
            (r"/manual_mode", ManualModeHandler),
            (r"/message", MessageHandler),
        ])

    def add_new_alert(self, alert: Alert):
        self.alert_db.add_new(alert)

def main():
    parser = argparse.ArgumentParser(description='Parses Zoohackathon 2017 alert CSVs.')
    parser.add_argument('path', type=str, help='Path of the CSV file.')
    parser.add_argument('number', type=str, help='Mock target telephone number.')
    args = parser.parse_args()

    global mock_target_number
    mock_target_number = args.number

    app = AlertApp()
    app.listen(8888)

    alert_csv_generator = watch_csv_log(args.path)
    def csv_watchdog():
        try:
            app.add_new_alert(next(alert_csv_generator))
        except:
            pass

    tornado.ioloop.PeriodicCallback(csv_watchdog, 1000).start()
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
