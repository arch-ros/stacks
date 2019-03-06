import re
import numbers
from enum import Enum

class Dependency:
    def __init__(self, name):
        self.name = name
    
    @staticmethod
    def parse(dep):
        return Dependency(dep)

class Version:
    def __init__(self, version, release, epoch):
        self.version = version
        self.release = release
        self.epoch = epoch

    def __str__(self):
        v = '.'.join(self.version)
        if len(self.release) > 0:
            v = v + '-' + '.'.join(self.release)
        if self.epoch > 0:
            v = str(self.epoch) + ':' + v
        return v

    @staticmethod
    def parse(pkgver, pkgrel=None, epoch=None):
        version = (pkgver.split(':')[1] if ':' in pkgver else pkgver).split('-')[0].split('.')
        epoch_num = epoch if epoch is not None else (int(pkgver.split(':')[0]) if ':' in pkgver else 0)
        release = pkgrel.split('.') if pkgrel is not None else \
                    (pkgver.split('-')[1].split('.') if '-' in pkgver else [])
        return Version(version, release, epoch_num)

class Package:
    def __init__(self, name, description=None, version=None, arch=[], groups=[], 
                    provides=[], conflicts=[], replaces=[],
                    depends=[], make_depends=[], check_depends=[], opt_depends=[],
                    artifacts={}):
        self.name = name
        self.description = description
        self.version = version
        self.arch = arch
        self.groups = groups

        self.provides = provides
        self.conflicts = conflicts
        self.replaces = replaces

        # Dependency objects
        self.depends = depends
        self.make_depends = make_depends
        self.check_depends = check_depends
        self.opt_depends = opt_depends

        self.artifacts = artifacts

    def matches(self, other):
        return self.hash_str == other.hash_str

    def merge(self, other):
        self.name = self.name if self.name else other.name
        self.description = self.description if self.description and len(self.description) > 0 else other.description
        self.version = self.version if self.version and (not other.version or self.version > other.version) else other.version
        self.arch = self.arch if self.arch and len(self.arch) > 0 else other.arch

        self.groups = self.groups.extend(other.groups)

        self.provides.extend(other.provides)
        self.conflicts.extend(other.conflicts)
        self.replaces.extend(other.replaces)

        self.artifacts = {**self.artifacts, **other.artifacts}

    @property
    def hash_str(self):
        return self.name + ' ' + ('/'.join(self.arch) if self.arch else '')

    def __str__(self):
        return self.name + ' ' + (str(self.version) if self.version else None) + ' ' + ('/'.join(self.arch) if self.arch else '')

class DiffType(Enum):
    ADDED = 'added'
    MODIFIED = 'modified'
    REMOVED = 'removed'

class Diff:
    def __init__(type_, old_hash, new_hash):
        self.type = type_
        self.old_hash = old_hash
        self.new_hash = new_hash

class Database:
    def __init__(self, packages=[]):
        if len(packages) > 0:
            self._packages = { x.hash_str : x for x in packages }
        else:
            self._packages = {}

    def __iter__(self):
        for package in self._packages.values():
            yield package

    def __contains__(self, package):
        if not package.hash_str in self._packages:
            return False
        return self._packages[package.hash_str].matches(package)

    def __len__(self):
        return len(self._packages)

    def add(self, pkg):
        self._packages[pkg.hash_str] = pkg

    def remove(self, pkg):
        del self._packages[pkg.hash_str]

    # Calculate the diffs to get from this db to odb
    def diffs(self, odb):
        diffs = []
        for pkg in self:
            if pkg not in odb:
                diffs.append((DiffType.REMOVED, pkg))
        for pkg in odb:
            if pkg not in self:
                diffs.append((DiffType.ADDED, pkg))
        return diffs

    # Replaces this db with the other db
    # and returns the diffs needed to get there
    def replace(self, odb):
        diffs = []
        for pkg in odb:
            if pkg not in self:
                diffs.append((DiffType.ADDED, pkg))
                self.add(pkg)
            else:
                if self._packages[pkg.hash_str].merge(pkg):
                    diffs.append((DiffType.MODIFIED, self._packages[pkg.hash_str]))
        for pkg in self:
            if pkg not in odb:
                diffs.append((DiffType.REMOVED, pkg))
                self.remove(pkg)
        return diffs

    # Called to update the database,
    # returns a list of diffs that were made
    # different types of databases extend this
    def update(self):
        return []


    def __str__(self):
        return '\n'.join([str(x) for x in self._packages.values()])
