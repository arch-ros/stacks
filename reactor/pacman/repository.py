from ..package import Package, Version, Dependency, Database
from .pkgbuild import PkgBuild

import os
import pycman
import pyalpm

import logbook

logger = logbook.Logger(__name__)

class BinaryDatabase(Database):
    def __init__(self, name, pacman_conf):
        super().__init__()
        self.name = name
        self._pacman_conf = pacman_conf
        self._pacman_handle = pycman.config.PacmanConfig(conf=self._pacman_conf).initialize_alpm()

        self.update()

    def update(self):
        new_db = Database()
        logger.debug('updating pacman databases for {}'.format(self.name))
        for db in self._pacman_handle.get_syncdbs():
            logger.debug('syncing {}...'.format(db.name))
            db.update(False)
            logger.debug('synced {}'.format(db.name))
        logger.debug('done synchronizing, reading package names')

        for db in self._pacman_handle.get_syncdbs():
            packages = db.search('')
            for pkg in packages:
                package = Package(name=pkg.name,
                                  version=Version.parse(pkg.version),
                                  arch=[pkg.arch],
                                  groups=pkg.groups,
                                  depends=[Dependency.parse(x) for x in pkg.depends],
                                  opt_depends=[Dependency.parse(x) for x in pkg.optdepends],
                                  make_depends=[],
                                  check_depends=[],
                                  provides=pkg.provides,
                                  replaces=pkg.replaces)
                new_db.add(package)
        return self.replace(new_db)

class SourceDatabase(Database):
    def __init__(self, name, directory, update_fs, find_dirs):
        super().__init__()
        self.name = name
        self._directory = directory
        self._update_fs = update_fs
        self._find_dirs = find_dirs

        self.update()

    def update(self):
        logger.debug('pulling source updates for {}'.format(self.name))
        if not self._update_fs(self, self._directory) and len(self) > 0:
            return [] # No changes

        new_db = Database()
        pkg_dirs = self._find_dirs(self, self._directory)

        logger.debug('scanning for changes'.format(self.name))
        for d in pkg_dirs:
            logger.trace('getting pkgbuild info of {}'.format(d))
            pkg = PkgBuild(os.path.join(d, 'PKGBUILD')).package_info
            pkg.artifacts['source_directory'] = d
            new_db.add(pkg)
        logger.debug('done scanning')
        return self.replace(new_db)
