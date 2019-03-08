from ..package import Package, Version, Dependency
from ..database import Database
from .pkgbuild import PkgBuild

import os
import pycman
import pyalpm

import logbook

class BinaryDatabase(Database):
    def __init__(self, name, pacman_conf):
        super().__init__(name)
        self._logger = logbook.Logger(name)

        self._pacman_conf = pacman_conf
        self._pacman_handle = pycman.config.PacmanConfig(conf=self._pacman_conf).initialize_alpm()

        self.update()

    def update(self):
        new_db = Database()
        self._logger.debug('updating pacman databases for {}'.format(self.name))
        for db in self._pacman_handle.get_syncdbs():
            self._logger.debug('syncing {}...'.format(db.name))
            db.update(False)
            self._logger.debug('synced {}'.format(db.name))
        self._logger.debug('done synchronizing, reading package names')

        for db in self._pacman_handle.get_syncdbs():
            packages = db.search('')
            for pkg in packages:
                package = Package(type='pacman',
                                  name=pkg.name,
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
        self.replace(new_db)

class SourceDatabase(Database):
    def __init__(self, name, directory, find_dirs):
        super().__init__(name)
        self._logger = logbook.Logger(name)
        self._directory = directory
        self._find_dirs = find_dirs

        self.update()

    def update(self):
        new_db = Database()
        pkg_dirs = self._find_dirs(self, self._directory)

        self._logger.debug('scanning for changes'.format(self.name))
        for d in pkg_dirs:
            self._logger.trace('getting pkgbuild info of {}'.format(d))
            pkg = PkgBuild(os.path.join(d, 'PKGBUILD')).package_info
            pkg.artifacts['source_directory'] = d
            new_db.add(pkg)
        self._logger.debug('done scanning')
        self.replace(new_db)
