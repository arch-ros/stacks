import threading

import logbook
import sys

class BuildQueue:
    def __init__(self, name, compiled_db, source_db, builder_pool):
        self.name = name
        self.logger = logbook.Logger(name)

        self.compiled_db = compiled_db
        self.source_db = source_db

        self.cron_jobs = []

        self.builders = list(builder_pool)
        self.free_builders = list(builder_pool)

        self.build_queue = []
        self.running_jobs = []

        self._success_hooks = []
        self._failure_hooks = []

        self._lock = threading.Lock()

    def add_success_hook(self, hook):
        with self._lock:
            self._success_hooks.append(hook)

    def add_failure_hook(self, hook):
        with self._lock:
            self._failure_hooks.append(hook)

    def update_queue(self):
        with self._lock:
            for pkg in self.source_db:
                if pkg in self.compiled_db:
                    continue
                if pkg in self.build_queue:
                    continue
                
                matching_builders = list(filter(lambda b: b.wants(pkg), self.builders))
                if len(matching_builders) > 0:
                    job = matching_builders[0].create_job(str(pkg), pkg)
                    self.logger.info('queuing build of {}'.format(pkg))
                    self.build_queue.append(job)
                else:
                    self.logger.warn('could not find builders for {}'.format(pkg))

    def run_jobs(self):
        # Assign all builders in the pool to jobs
        with self._lock:
            while len(self.build_queue) > 0:
                job = self.build_queue[0]
                available_builders = list(filter(lambda b: job.wants(b), self.free_builders))
                if len(available_builders) > 0:
                    builder = available_builders[0]
                    # Remove builder, job from queue
                    self.free_builders.remove(builder)
                    self.build_queue.pop(0)

                    self.running_jobs.append(job)
                    job.start(self, builder)

    def job_failed(self, job, builder):
        with self._lock:
            self.logger.info('job failed {}'.format(job.name))
            self.logger.info('freeing builder for job {}'.format(job.name))
            
            # Put builder back in the pool
            self.free_builders.append(builder)

            for h in self._failure_hooks:
                h(job)

    def job_finished(self, job, builder):
        with self._lock:
            self.logger.info('freeing builder for job {}'.format(job.name))

            # Put builder back in the pool
            self.free_builders.append(builder)
            for h in self._success_hooks:
                h(job)

class Job:
    def __init__(self, name, type_):
        self.name = name
        self.type = type_
        self.status = 'not started'
        self.info = {}
        self.artifacts = {}
        self.logger = logbook.Logger(name)

    def wants(self, builder):
        return True

    def start(self, queue, builder):
        def finish():
            try:
                result = self.run(builder)
            except:
                queue.job_failed(self, builder)
                logger.exception('Unexcepted exception while running job {}'.format(self.name))
                return

            if result:
                queue.job_finished(self, builder)
            else:
                queue.job_failed(self, builder)

        thread = threading.Thread(target=finish)
        thread.start()

    def run(self, builder):
        # Should never be called!
        raise NotImplementedError()

class Builder:
    def __init__(self, name, types_):
        self.name = name
        self.types = types_
        self.logger = logbook.Logger(name)

    def wants(self, package):
        return True

    def create_job(self, job_name, package):
        raise NotImplementedError()
