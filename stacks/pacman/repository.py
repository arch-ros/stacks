import subprocess
import os
import shutil
import asyncio

import logbook
from .. import util

class Repository:
    def __init__(self, dir_path, db_path):
        self._dir_path = dir_path
        self._db_path = db_path
        self._lock = asyncio.Lock()

        if not os.path.isdir(self._dir_path):
            os.makedirs(self._dir_path)

    async def clear(self, logger=None):
        pass

    async def add(self, package_path, logger=None):
        # Copy file to directory
        file_name = os.path.basename(package_path)
        target_path = os.path.join(self._dir_path, file_name)

        if logger:
            logger.debug('copying {} to {}'.format(package_path, target_path))
        shutil.copy2(package_path, target_path)

        # Wait until the lock is gone
        if logger:
            logger.info('adding {}'.format(file_name))
        async with self._lock:
            if not (await util.run_proc_async(['repo-add', self._db_path, target_path],
                                                logger=logger)):
                raise IOError('Unable to add package')


    async def remove(self, package_name, logger=None):
        self._logger.info('removing {}'.format(package_name))
        if not (await util.run_proc_async(['repo-remove', self._db_path, package_name],
                                            logger=logger)):
            raise IOError('Unable to add package')
