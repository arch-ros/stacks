import threading

import logbook
import sys
import datetime
import json
import os

from enum import Enum

class EventType(Enum):
    BUILD = 'build'

class Event:
    def __init__(self, type, tag):
        self.type = type
        self.tag = tag

    @property
    def pack(self):
        raise NotImplementedError()

    @staticmethod
    def unpack(value):
        if value['type'] == EventType.BUILD.value:
            return Build.unpack(value)

class EventLog:
    def __init__(self):
        self.history = []
        self.current_id = 0

    def save(self, filepath):
        data = [x.pack for x in self.history]
        with open(filepath, 'w') as f:
            json.dump(data, f)

    def load(self, filepath):
        if not os.path.isfile(filepath):
            return
        with open(filepath) as f:
            data = json.load(f)
            for e in data:
                self.history.append(Event.unpack(e))

            # update the current_id
            for e in self.history:
                if hasattr(e, 'id'):
                    self.current_id = max(e.id, self.current_id)

    def get_build_by_id(self, id):
        for event in self.history:
            if hasattr(event, 'id'):
                if event.type == EventType.BUILD and event.id == id:
                    return event
        return None

    def get_events_by_tag(self, tag):
        events = []
        for event in self.history:
            if hasattr(event, 'tag'):
                if event.tag == tag:
                    events.append(event)
        return events

    def create_build(self, tag, name, worker_name):
        build = Build(self.current_id + 1, tag, name, worker_name)
        self.current_id = self.current_id + 1

        self.history.append(build)
        return build

class BuildStatus(Enum):
    WAITING = 'waiting'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILURE = 'failure'

class Build(Event):
    def __init__(self, id, tag, name, worker, 
                        log='', artifacts={}, status=BuildStatus.WAITING,
                        started=None, ended=None):
        super().__init__(EventType.BUILD, tag)
        self.id = id
        self.name = name
        self.worker = worker
        self.log = log
        self.artifacts = dict(artifacts) # Outputs
        self.status = status
        self.started = started
        self.ended = ended

    @property
    def logger(self):
        b = self
        fmt = '[{record.time:%Y-%m-%d %H:%M:%S.%f%z}] {record.extra[worker]}: {record.message}\n'
        formatter = logbook.handlers.StringFormatter(fmt)
              
        class CustomLogger(logbook.Logger):
            def process_record(self, record):
                logbook.Logger.process_record(self, record)
                record.extra['worker'] = b.worker
                b.log += formatter(record, None)

        return CustomLogger(self.name)

    def started_now(self):
        self.started = datetime.datetime.now()

    def ended_now(self):
        self.ended = datetime.datetime.now()

    def set_running(self):
        self.status = BuildStatus.RUNNING

    def set_success(self):
        self.status = BuildStatus.SUCCESS

    def set_failure(self):
        self.status = BuildStatus.FAILURE

    def add_artifact(self, name, artifact):
        self.artifacts[name] = artifact

    @property
    def pack(self):
        return {'type' : EventType.BUILD.value,
                'id': self.id,
                'name': self.name,
                'tag': self.tag,
                'status': self.status.value,
                'worker': self.worker,
                'artifacts': self.artifacts,
                'started': self.started.strftime('%m/%d/%Y %H:%M:%S'),
                'ended': self.ended.strftime('%m/%d/%Y %H:%M:%S') if self.ended else '',
                'log': self.log}

    @staticmethod
    def unpack(value):
        return Build(int(value['id']), value['tag'], value['name'], value['worker'],
                         value['log'], value['artifacts'], BuildStatus(value['status']),
                         datetime.datetime.strptime(value['started'], '%m/%d/%Y %H:%M:%S') if len(value['started']) > 0 else None,
                         datetime.datetime.strptime(value['ended'], '%m/%d/%Y %H:%M:%S') if len(value['ended']) > 0 else None)
