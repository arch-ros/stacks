import subprocess
import os
import shutil

import logbook
from .. import util

class Repository:
    def __init__(self, name, dir_path, db_path):
        self.name = name
        self._logger = logbook.Logger(name)
        self._dir_path = dir_path
        self._db_path = db_path

        if not os.path.isdir(self._dir_path):
            os.makedirs(self._dir_path)

    def clear(self):
        self._logger.info('deleting repository')

    def add(self, package_path):
        # Copy file to directory
        file_name = os.path.basename(package_path)
        target_path = os.path.join(self._dir_path, file_name)

        self._logger.debug('copying {} to {}'.format(package_path, target_path))
        shutil.copy2(package_path, target_path)

        self._logger.info('adding {}'.format(file_name))
        if not util.run_proc(['repo-add', self._db_path, target_path],
                                logger=self._logger):
            raise IOError('Unable to add package')


    def remove(self, package_name):
        self._logger.info('removing {}'.format(package_name))
        if not util.run_proc(['repo-remove', self._db_path, package_name],
                                logger=self._logger):
            raise IOError('Unable to add package')
