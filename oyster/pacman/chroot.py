import tempfile
import subprocess
import threading
from ..job import Worker, Job
import sys
import os
from .. import util

import logbook

class ChrootWorker(Worker):
    def __init__(self, name, root, pacman_conf, bind_dir, mkrootcmd, mkpkgcmd):
        super().__init__(name)
        self._chroot = root
        self._pacman_conf = pacman_conf
        self._bind_dir = bind_dir
        self._mkrootcmd = mkrootcmd
        self._mkpkgcmd = mkpkgcmd

        if not os.path.isdir(os.path.join(self._chroot, 'root')):
            self.logger.info('creating chroot at {}'.format(self._chroot))
            if not os.path.isdir(self._chroot):
                os.makedirs(self._chroot)
        
            # Make arch chroot
            args = [self._mkrootcmd, '-C', pacman_conf, os.path.join(self._chroot, 'root'), 'base-devel']
            self.logger.trace('running {}'.format(' '.join(args)))
            if not util.run_proc(args, self.logger, self._chroot):
                raise IOError('Failed to create chroot')
            self.logger.info('done creating chroot')

    # Run an actual job
    async def _exec(self, job, build):
        build.started_now()
        build.set_running()

        src_dir = job.package.artifacts['source_directory']

        result_file = job.package.name + '-' + str(job.package.version) + \
                        '-' + '-'.join(job.package.arch) + '.pkg.tar.xz'
        result_path = os.path.join(src_dir, result_file)

        # check if already built
        if os.path.exists(result_path):
            self.logger.debug('package file found {}'.format(result_file))

            build.add_artifact('binary_files', [result_path])
            build.ended_now()
            build.set_success()
            return
            
        # not already built, do build
        self.logger.info('starting build {}'.format(self.name))
        args = [self._mkpkgcmd, '-d', self._bind_dir, '-r', self._chroot, '.']
        self.logger.trace('running {}'.format(' '.join(args)))
        if not (await util.run_proc_async(args, self.logger, src_dir)):
            build.add_artifact('binary_files', [])
            build.ended_now()
            build.set_failure()
            return

        if os.path.exists(result_path):
            self.logger.debug('package file found {}'.format(result_file))
            build.add_artifact('binary_files', [result_path])
            build.ended_now()
            build.set_failure()
            return
        else:
            self.logger.error('could not find result file {}'.format(result_file))
            build.add_artifact('binary_files', [])
            build.ended_now()
            build.set_failure()
            return


    async def run(self, event_log, queue):
        while True:
            # Will do other queue actions
            # while we wait
            job = await queue.get()
            build = event_log.create_build(job.tag)
            await self._exec(job, build)
            # notify listeners
            for l in self.listeners:
                l(job, build)
            queue.task_done()
