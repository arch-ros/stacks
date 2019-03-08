import threading

import logbook
import sys
import datetime

from enum import Enum

class EventType(Enum):
    BUILD = 'build'

class Event:
    def __init__(self, type):
        self.type = type

class EventLog:
    def __init__(self):
        self.history = []
        self.current_id = 0

    def create_build(self, tag):
        build = Build(self.current_id + 1, tag)
        self.current_id = self.current_id + 1

        self.history.append(build)
        return build

class BuildStatus(Enum):
    WAITING = 'waiting'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILURE = 'failure'

class Build(Event):
    def __init__(self, id, tag):
        super().__init__(EventType.BUILD)
        self.id = id
        self.tag = tag
        self.artifacts = {} # Outputs
        self.logger = logbook.Logger(tag)
        self.status = BuildStatus.WAITING
        self.started = None
        self.ended = None

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
