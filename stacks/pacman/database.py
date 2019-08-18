from ..package import Package, Version, Dependency
from ..database import Database
from .pkgbuild import PkgBuild

import os
import pycman
import pyalpm

import logbook

def _from_alpm_pkg(pkg):
    package = Package(type='pacman',
                      name=pkg.name,
                      version=Version.parse(pkg.version),
                      arch=[pkg.arch],
                      groups=pkg.groups,
                      depends={Dependency.parse(x) for x in pkg.depends},
                      opt_depends={Dependency.parse(x) for x in pkg.optdepends},
                      make_depends=set(),
                      check_depends=set(),
                      provides={Dependency.parse(x) for x in pkg.provides},
                      replaces={Dependency.parse(x) for x in pkg.replaces},
                      conflicts={Dependency.parse(x) for x in pkg.conflicts},
                      parent=pkg.base if pkg.base != pkg.name else None)
    return package

def _default_find_packages(db, directory):
    return list(map(lambda f: os.path.join(directory, f),
                filter(lambda f: f.endswith('.pkg.tar.xz'),
                                 os.listdir(directory))))

class RemoteDatabase(Database):
    def __init__(self, name, pacman_conf, update_once=False):
        super().__init__(name)
        self._logger = logbook.Logger(name)

        self._pacman_conf = pacman_conf
        self._pacman_handle = pycman.config.PacmanConfig(conf=self._pacman_conf).initialize_alpm()

        # If update_once is set only run on constructor
        self._update_once = False
        if update_once:
            self.update()
            self._update_once = update_once

    def update(self):
        if self._update_once:
            return

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
                package = _from_alpm_pkg(pkg)
                new_db.add(package)
        self.replace(new_db)

class BinaryDatabase(Database):
    def __init__(self, name, directory, find_packages=_default_find_packages):
        super().__init__(name)
        self._logger = logbook.Logger(name)
        self._directory = directory
        self._find_packages = find_packages

        self._pacman_handle = pyalpm.Handle('/', '/var/lib/pacman')
        self.update()

    def update(self):
        new_db = Database()
        self._logger.debug('scanning for changes for {}'.format(self.name))
        pkgs = self._find_packages(self, self._directory)
        for pkg_path in pkgs:
            self._logger.trace('getting package info for {}'.format(pkg_path))
            pkg = self._pacman_handle.load_pkg(pkg_path)
            new_db.add(_from_alpm_pkg(pkg))
        self.replace(new_db)

class SourceDatabase(Database):
    def __init__(self, name, directory, find_dirs):
        super().__init__(name)
        self._logger = logbook.Logger(name)
        self._directory = directory
        self._find_dirs = find_dirs

    def update(self):
        new_db = Database()
        pkg_dirs = self._find_dirs(self, self._directory)

        self._logger.debug('scanning for changes for {}'.format(self.name))
        for d in pkg_dirs:
            self._logger.trace('getting pkgbuild info of {}'.format(d))
            packages = PkgBuild(os.path.join(d, 'PKGBUILD')).packages
            for p in packages:
                p.artifacts['source_directory'] = d
                new_db.add(p)
        self._logger.debug('done scanning')
        self.replace(new_db)
