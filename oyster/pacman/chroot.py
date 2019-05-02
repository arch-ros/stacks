import tempfile
import subprocess
import threading
from ..job import Worker, Job
import sys
import os
from .. import util
from .pkgbuild import PkgBuild

import logbook
import inspect

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
        logger = build.logger

        build.started_now()
        build.set_running()

        src_dir = job.package.artifacts['source_directory']
        pkgbuild = PkgBuild(os.path.join(src_dir, 'PKGBUILD'))
        pkgs = pkgbuild.packages

        # Result files contains a set of option per file name
        result_files = [[p.name + '-' + str(p.version) + '-' + \
                        a + '.pkg.tar.xz' for a in p.arch] for p in pkgs]
        result_paths = [[os.path.join(src_dir, fn) for fn in f] for f in result_files]

        # This could probably be rewritten functionally to be very beautiful
        def collect_files():
            result_files = []
            for options in result_paths:
                for f in options:
                    if os.path.exists(f):
                        result_files.append(f)
            return result_files

        # check if already built
        if len(collect_files()) == len(result_paths):
            files = collect_files()
            logger.debug('package files found: {}'.format(', '.join(files)))
            build.add_artifact('binary_files', files)
            build.ended_now()
            build.set_success()
            return
            
        # not already built, do build
        logger.info('starting build {}'.format(self.name))
        args = [self._mkpkgcmd, '-d', self._bind_dir, '-r', self._chroot, '.']
        logger.trace('running {}'.format(' '.join(args)))
        if not (await util.run_proc_async(args, logger, src_dir)):
            build.add_artifact('binary_files', [])
            build.ended_now()
            build.set_failure()
            return

        if len(collect_files()) == len(result_paths):
            files = collect_files()
            logger.debug('package files found {}'.format(', '.join(files)))
            build.add_artifact('binary_files', files)
            build.ended_now()
            build.set_success()
            return
        else:
            logger.error('could not find result files')
            build.add_artifact('binary_files', [])
            build.ended_now()
            build.set_failure()
            return

    async def run(self, event_log, queue):
        while True:
            # Will do other queue actions
            # while we wait
            job = await queue.get()
            build = event_log.create_build(job.tag, str(job.package), self.name)
            await self._exec(job, build)
            # notify listeners
            for l in self.listeners:
                if inspect.iscoroutinefunction(l):
                    await l(job, build)
                else:
                    l(job, build)
            queue.task_done(job)
