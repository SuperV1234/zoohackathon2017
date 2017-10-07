#!/usr/bin/python3

import time
import pygtail
import argparse
import pprint
import sys
import uuid
import tornado.httpserver
import tornado.ioloop
import tornado.web

class Alert(object):
    def __init__(self, name, sn, time, date, position, label, state, xuuid = None):
        self.uuid = uuid.uuid4() if xuuid == None else xuuid
        self.name = name
        self.sn = sn
        self.time = time
        self.date = date
        self.position = position
        self.label = label
        self.state = state
        self.target = AlertTarget(None)

    def __repr__(self) -> str:
        return f'''Alert[{self.uuid}]
{{
    name: {self.name}
    sn: {self.sn}
    time: {self.time}
    date: {self.date}
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
        "time": alert.time,
        "date": alert.date,
        "label": alert.label,
        "target": alert.target.to_json(),
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

class AlertDB(object):
    def __init__(self):
        self.alerts = []
        self.uuid_to_alert = {}

    def add_new(self, alert: Alert, manual_mode: bool):
        self.alerts.append(alert)
        xuuid = alert.uuid

        verbose_print(f'[AlertDB]: Added new alert\n{alert}\n')
        self.uuid_to_alert[xuuid] = alert

        if manual_mode == True:
            verbose_print(f'[AlertDB]: {xuuid} now requires manual intervention')
            alert.state = "to_manually_dispatch"
        else:
            verbose_print(f'[AlertDB]: {xuuid} now requires ackwnowledgement')

            # TODO: implement real dispatching strategy here
            alert.state = "to_acknowledge"
            alert.target = AlertTarget("+441234567890")

    def from_uuid(self, uuid) -> Alert:
        return self.uuid_to_alert[uuid]

    def _uuid_map(self, src) -> [Alert]:
        return list(map(self.from_uuid, src))

    def get_with_state(self, state) -> [Alert]:
        return [x for x in self.alerts if x.state == state]

    def move_between_states(self, uuid, old, new) -> bool:
        if self.from_uuid(uuid).state == old:
            self.from_uuid(uuid).state = new

            if old == "to_manually_dispatch" and new == "to_acnowledge":
                # TODO: implement manual dispatch
                pass

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

class AlertApp(tornado.web.Application):
    def __init__(self):
        self.alert_db = AlertDB()
        self.manual_mode = False

        super(AlertApp, self).__init__([
            (r"/", MainHandler),
        ])

    def add_new_alert(self, alert: Alert):
        self.alert_db.add_new(alert, self.manual_mode)

def main():
    parser = argparse.ArgumentParser(description='Parses Zoohackathon 2017 alert CSVs.')
    parser.add_argument('path', type=str, help='Path of the CSV file.')
    args = parser.parse_args()

    app = AlertApp()
    app.listen(8888)

    def csv_watchdog():
        for alert in watch_csv_log(args.path):
            # pprint.pprint(alert)
            app.add_new_alert(alert)

    tornado.ioloop.PeriodicCallback(csv_watchdog, 100).start()
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
