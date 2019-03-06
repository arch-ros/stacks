import threading

import logbook
import sys

logger = logbook.Logger(__name__)

class BuildQueue:
    def __init__(self, compiled_db, source_db, builder_pool,
                        package_filter=lambda x: True):
        self.compiled_db = compiled_db
        self.source_db = source_db
        self.package_filter = package_filter

        self.builder_pool = list(builder_pool)

        self.build_queue = []
        self.current_jobs = []

        self._lock = threading.Lock()

    def update_queue(self):
        with self._lock:
            for pkg in self.source_db:
                if self.package_filter(pkg):
                    if not pkg in self.compiled_db and \
                       not pkg in self.build_queue:
                        logger.info('queuing build of {}'.format(pkg))
                        self.build_queue.append(pkg)

    def run_jobs(self):
        # Assign all builders in the pool to jobs
        with self._lock:
            while len(self.builder_pool) > 0 and len(self.build_queue) > 0:
                builder = self.builder_pool.pop(0)
                pkg = self.build_queue.pop(0)
                name = pkg.hash_str

                job = builder.create_job(str(pkg), self, pkg)
                self.current_jobs.append(job)
                job.start()

    def job_failed(self, job):
        with self._lock:
            logger.info('job failed {}'.format(job.name))
            logger.info('freeing builder for job {}'.format(job.name))
            
            # Put builder back in the pool
            self.builder_pool.append(job.builder)

    def job_finished(self, job):
        with self._lock:
            logger.info('freeing builder for job {}'.format(job.name))

            # Put builder back in the pool
            self.builder_pool.append(job.builder)

class Job:
    def __init__(self, name, queue, builder, package):
        self.name = name
        self.queue = queue
        self.builder = builder
        self.package = package

        def finish():
            try:
                result = self.run()
            except:
                queue.job_failed(self)
                logger.exception('Unexcepted exception while running job {}'.format(self.name))
                return

            if result:
                queue.job_finished(self)
            else:
                queue.job_failed(self)

        self._thread = threading.Thread(target=finish)

    def start(self):
        self._thread.start()

    def run(self):
        # Should never be called!
        raise NotImplementedError()

class Builder:
    def __init__(self, name):
        self.name = name

    def create_job(self, job_name, queue, package):
        return None
