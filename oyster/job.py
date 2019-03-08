import threading
import logbook
import asyncio
import datetime

from .database import DerivedDatabase
from .package import Package

logger = logbook.Logger(__name__)

# A job is something that is queued or running
# it can be requeued and each time will produce a new build object
class Job:
    def __init__(self, time, tag, package):
        self.time = time
        self.tag = tag
        self.package = package

    def produces(self, package):
        return package.name == self.package.name or \
               (package.parent is not None and package.parent == self.package.parent)

# Workers process jobs
class Worker:
    def __init__(self, name):
        self.name = name
        self.logger = logbook.Logger(name)
        self.listeners = []

    def add_listener(self, l):
        self.listeners.append(l)

    # Tell the worker to take from the queue, indefinitely
    async def run(self, event_log, queue):
        raise NotImplementedError()

class Queue(asyncio.Queue):
    @property
    def waiting(self):
        return list(self._queue)

class Scheduler:
    def __init__(self, binaries, sources):
        self._binaries = binaries
        self._sources = sources

        self._unbuilt = DerivedDatabase('unbuilt', [self._sources],
                            filter=lambda pkg: not pkg in self._binaries)

        # build queue
        self.queue = Queue()
        # things this scheduler has scheduled
        # so we don't accidentally re-schedule them
        self._scheduled = set()

    async def schedule_loop(self):
        while True:
            # only schedule more things if something
            # has changed with the queue
            await self.queue.join()
            self._unbuilt.update()
            for pkg in self._unbuilt:
                # if this package is not produced
                # by anything we have previously scheduled
                if not any([j.produces(pkg) for j in self._scheduled]):
                    tag = pkg.name
                    job = Job(datetime.datetime.now(), tag, pkg)
                    self._scheduled.add(job)
                    logger.info('queuing {}'.format(str(pkg)))
                    await self.queue.put(job)
            if self.queue.empty():
                await asyncio.sleep(60)

    async def run(self, event_log, workers):
        # we have two tasks: 
        # run the workers
        # run the schedule loop
        schedule_task = asyncio.create_task(self.schedule_loop())
        worker_tasks = [ asyncio.create_task(w.run(event_log, self.queue)) for w in workers ]

        # run the things!
        await asyncio.gather(schedule_task, *worker_tasks)
