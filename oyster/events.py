import threading

import logbook
import sys
import datetime

from enum import Enum

class EventType(Enum):
    BUILD = 'build'

class Event:
    def __init__(self, type, tag):
        self.type = type
        self.tag = tag

class EventLog:
    def __init__(self):
        self.history = []
        self.current_id = 0

    def get_build_by_id(self, id):
        for event in self.history:
            if event.type == EventType.BUILD and event.id == id:
                return event
        return None

    def get_events_by_tag(self, tag):
        events = []
        for event in self.history:
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
    def __init__(self, id, tag, name, worker):
        super().__init__(EventType.BUILD, tag)
        self.id = id
        self.name = name
        self.worker = worker
        self.log = ''
        self.artifacts = {} # Outputs
        self.status = BuildStatus.WAITING
        self.started = None
        self.ended = None

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
