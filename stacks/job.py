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

    def missing_depends(self, depends_resolver):
        dependencies = self.package.depends | self.package.make_depends
        return list(filter(lambda x: not x.satisfied_by(depends_resolver), dependencies))

    def produces(self, package):
        my_name = self.package.parent if self.package.parent is not None else self.package.name
        other_name = package.parent if package.parent is not None else package.name
        return my_name == other_name

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
    def __init__(self, maxsize=0, *, loop=None):
        super().__init__(maxsize=maxsize, loop=loop)
        self._running = set()

    def _get(self):
        elem = self._queue.popleft()
        self._running.add(elem)
        return elem

    def task_done(self, task):
        super().task_done()
        self._running.remove(task)

    @property
    def waiting(self):
        return list(self._queue)

    @property
    def running(self):
        return set(self._running)

    @property
    def tasks(self):
        return list(self.running) + self.waiting

class CronTask:
    def __init__(self):
        pass

    @property
    def name(self):
        raise NotImplementedError()

    @property
    def next_job(self):
        raise NotImplementedError()

    @property
    def next_time(self):
        raise NotImplementedError()

    def produces(self, package):
        raise NotImplementedError()

    def start(self, scheduler):
        pass

    def stop(self, scheduler):
        pass

class Reschedule(CronTask):
    def __init__(self, job, delay):
        self.job = job
        self.delay = delay
        self.time = None

    @property
    def name(self):
        return 'Reschedule ' + self.job.tag

    @property
    def next_job(self):
        return self.job

    @property
    def next_time(self):
        return self.time

    def produces(self, package):
        return self.job.produces(package)

    async def run(self, scheduler):
        self.time = datetime.datetime.now() + \
                    datetime.timedelta(seconds=self.delay)
        await asyncio.sleep(self.delay)
        scheduler.enqueue(self.job)
        scheduler.unschedule(self)

    def start(self, scheduler):
        loop = asyncio.get_running_loop()
        loop.call_soon(lambda: asyncio.create_task(self.run(scheduler)))

    def stop(self, scheduler):
        pass


class Scheduler:
    def __init__(self, binaries, sources, dependency_resolver=None):
        self._binaries = binaries
        self._sources = sources
        self.depends_resolver = dependency_resolver
        self.cron_tasks = list()

        # Things are taken from
        # waiting an put in the build
        # queue when they can be built
        self.waiting = set()
        self.queue = Queue()

    async def enqueue(self, job):
        logger.info('queuing {}'.format(job.tag))
        await self.queue.put(job)

    def schedule(self, task):
        self.cron_tasks.append(task)
        task.start(self)

    def unschedule(self, task):
        task.stop(self)
        self.cron_tasks.remove(task)

    async def schedule_loop(self):
        while True:
            # only schedule more things if 
            # the queue is empty
            await self.queue.join()

            self._binaries.update()
            self._sources.update()
            self.depends_resolver.update()
            for pkg in self._sources:
                if pkg in self._binaries:
                    continue
                # if this package is produced
                # by anything we have previously scheduled
                if any([j.produces(pkg) for j in self.cron_tasks]):
                    continue
                if any([j.produces(pkg) for j in self.queue.tasks]):
                    continue
                if any([j.produces(pkg) for j in self.waiting]):
                    continue

                job = Job(datetime.datetime.now(), pkg.tag, pkg)
                self.waiting.add(job)

            for job in set(self.waiting):
                missing_depends = job.missing_depends(self.depends_resolver)
                if len(missing_depends) == 0:
                    self.waiting.remove(job)
                    await self.enqueue(job)

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
