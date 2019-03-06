import tempfile
import subprocess
from ..builder import Builder, Job
import sys
import os

import logbook

# Docker builder/job
class ChrootJob(Job):
    def __init__(self, job_name, package):
        super().__init__(job_name, 'chroot_package')
        self.package = package

    def run(self, builder):
        chroot = builder._chroot
        src_dir = self.package.artifacts['source_directory']

        result_file = self.package.name + '-' + str(self.package.version) + \
                        '-' + '-'.join(self.package.arch) + '.pkg.tar.xz'
        result_path = os.path.join(src_dir, result_file)

        # check if already built
        if os.path.exists(result_path):
            self.artifacts['binary_file'] = result_path
            self.logger.debug('package file found {}'.format(result_file))
            return True

        self.logger.info('starting build {}'.format(self.name))
        with subprocess.Popen([builder._mkpkgcmd, '-r', chroot, '.'],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                cwd=src_dir) as proc:
            with proc.stdout:
                for line in iter(proc.stdout.readline, b''):
                    self._logger.trace(line.decode('utf-8').strip())
            exitcode = proc.wait()
            self.logger.info('build {} finished'.format(self.name))
            if exitcode != 0:
                return False

        if os.path.exists(result_path):
            self.artifacts['binary_file'] = result_path
            self.logger.debug('package file found {}'.format(result_file))
            return True
        self.logger.error('could not find result file {}'.format(result_file))
        return False

class ChrootBuilder(Builder):
    def __init__(self, name, directory, mkrootcmd, mkpkgcmd):
        super().__init__(name, ['chroot_package'])
        self._chroot = directory
        self._mkrootcmd = mkrootcmd
        self._mkpkgcmd = mkpkgcmd

        if not os.path.isdir(self._chroot):
            self.logger.info('creating chroot at {}'.format(self._chroot))
            os.makedirs(self._chroot)
        
            # Make arch chroot
            with subprocess.Popen([self._mkrootcmd, os.path.join(directory,'root'), 'base-devel'],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    cwd=directory) as proc:
                with proc.stdout:
                    for line in iter(proc.stdout.readline, b''):
                        self.logger.trace(line.decode('utf-8').strip())
            self._logger.info('done creating chroot')
    
    def create_job(self, job_name, package):
        return ChrootJob(job_name, package)
