import tempfile
import subprocess
from .builder import Builder, Job
import sys
import os

import logbook

# Docker builder/job
class ChrootJob(Job):
    def __init__(self, job_name, queue, builder, package):
        super().__init__(job_name, queue, builder, package)
        self._logger = logbook.Logger(job_name + '|' + builder.name)

    def run(self):
        chroot = self.builder._chroot
        src_dir = self.package.artifacts['source_directory']
        self._logger.info('starting build {}'.format(self.name))
        with subprocess.Popen([self.builder._mkpkgcmd, '-r', chroot, '.'],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                cwd=src_dir) as proc:
            with proc.stdout:
                for line in iter(proc.stdout.readline, b''):
                    self._logger.trace(line.decode('utf-8').strip())
            exitcode = proc.wait()
            self._logger.info('build {} finished'.format(self.name))
            if exitcode != 0:
                return False

            return True



class ChrootBuilder(Builder):
    def __init__(self, name, directory, mkrootcmd, mkpkgcmd):
        super().__init__(name)
        self._chroot = directory
        self._mkrootcmd = mkrootcmd
        self._mkpkgcmd = mkpkgcmd
        self._logger = logbook.Logger(name)

        if not os.path.isdir(self._chroot):
            self._logger.info('creating chroot at {}'.format(self._chroot))
            os.makedirs(self._chroot)
        
            # Make arch chroot
            with subprocess.Popen([self._mkrootcmd, os.path.join(directory,'root'), 'base-devel'],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    cwd=directory) as proc:
                with proc.stdout:
                    for line in iter(proc.stdout.readline, b''):
                        self._logger.trace(line.decode('utf-8').strip())
            self._logger.info('done creating chroot')
    
    def create_job(self, job_name, queue, package):
        return ChrootJob(job_name, queue, self, package)
