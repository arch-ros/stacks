import re
import numbers
from enum import Enum

import copy

class Dependency:
    # Consists of a name, a min version, a max version, and whether those are inclusive bounds
    def __init__(self, name, min_version=None, max_version=None):
        self.name = name
        self.min_version = min_version
        self.max_version = max_version

    # Check to see if the dependencies
    # are satisfied by the binaries repository
    def satisfied_by(self, resolver):
        if resolver is None: # If we don't have a resolver, just assume we can build
            return True
        return len(resolver.find(self.name)) > 0

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
    
    @staticmethod
    def parse(dep):
        if ':' in dep:
            dep = dep.split(':')[0]
        if '>=' in dep:
            name, version = tuple(dep.split('>='))
            return Dependency(name, min_version=Version.parse(version))
        if '<=' in dep:
            name, version = tuple(dep.split('<='))
            return Dependency(name, max_version=Version.parse(version))
        if '=' in dep:
            name, version = tuple(dep.split('='))
            v = Version.parse(version)
            return Dependency(name, min_version=v, max_version=v)
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
    def __init__(self, type, name, description=None, version=None, arch=[], groups=[], 
                    provides=[], conflicts=[], replaces=[],
                    depends=[], make_depends=[], check_depends=[], opt_depends=[],
                    artifacts={}, parent=None):
        self.type = type
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
        self.parent = parent

    @property
    def tag(self):
        return self.parent if self.parent else self.name

    @property
    def hash_str(self):
        return self.type + ' ' + self.name + ' ' + ('/'.join(self.arch) if self.arch else '')

    def matches(self, other):
        return self.hash_str == other.hash_str

    # Replaces this package info with the others
    def replace(self, other):
        self.name = other.name
        self.description = other.description
        self.version = other.version
        self.arch = other.arch
        self.groups = other.groups
        self.provides = other.provides
        self.conflicts = other.conflicts
        self.replaces = other.replaces
        self.artifacts = other.artifacts
        self.parent = other.parent

    # Fills in additional info from other package
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
        self.parent = self.parent if self.parent else other.parent


    def clone(self):
        return copy.deepcopy(self)

    def __eq__(self, other):
        return self.name == other.name and self.version == other.version

    def __str__(self):
        return self.name + ' ' + (str(self.version) if self.version else None) + ' ' + ('/'.join(self.arch) if self.arch else '')

    def __hash__(self):
        return hash(self.type + ' ' + self.name + ' ' + '/'.join(self.arch) if self.arch else '')

