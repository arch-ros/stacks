import re
import numbers
from enum import Enum

import copy

class Dependency:
    # Consists of a name, a min version, a max version, and whether those are inclusive bounds
    def __init__(self, name, min_version=None, max_version=None,
                             min_incl=True, max_incl=True):
        self.name = name
        self.min_version = min_version
        self.max_version = max_version
        self.min_inclusive = min_incl
        self.max_inclusive = max_incl


    # Check to see if the dependencies
    # are satisfied by the binaries repository
    def satisfied_by(self, resolver):
        if resolver is None: # If we don't have a resolver, just assume we can build
            return True
        return len(resolver.find(self.name)) > 0

    def __str__(self):
        type = ''
        if self.min_version is not None:
            type = ('>=' if self.min_inclusive else '>') + str(self.min_version)
        if self.max_version is not None:
            type = ('<=' if self.max_inclusive else '<') + str(self.max_version)
        return self.name + type

    def __repr__(self):
        return str(self)
    
    @staticmethod
    def parse(dep):
        if ':' in dep:
            dep = dep.split(':')[0]
        if '>=' in dep:
            name, version = tuple(dep.split('>='))
            return Dependency(name, min_version=Version.parse(version), min_incl=True)
        if '<=' in dep:
            name, version = tuple(dep.split('<='))
            return Dependency(name, max_version=Version.parse(version), max_incl=True)
        if '<' in dep:
            name, version = tuple(dep.split('<'))
            return Dependency(name, max_version=Version.parse(version), max_incl=False)
        if '>' in dep:
            name, version = tuple(dep.split('>'))
            return Dependency(name, min_version=Version.parse(version), min_incl=False)
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
    def __init__(self, type, name, description=None, version=None, arch=set(), groups=set(), 
                    provides=set(), conflicts=set(), replaces=set(),
                    depends=set(), make_depends=set(), check_depends=set(), opt_depends=set(),
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
    def identifier(self):
        return self.type + ' ' + self.name + ' ' + str(self.version)

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

        self.depends = other.depends
        self.make_depends = other.make_depends
        self.check_depends = other.check_depends
        self.opt_depends = other.opt_depends

        self.artifacts = other.artifacts
        self.parent = other.parent

    # Fills in additional info from other package
    def merge(self, other):
        self.name = self.name if self.name else other.name
        self.description = self.description if self.description and len(self.description) > 0 else other.description
        self.version = self.version if self.version and (not other.version or self.version > other.version) else other.version
        self.arch = self.arch if self.arch and len(self.arch) > 0 else other.arch

        self.groups = self.groups.update(other.groups)

        self.provides.update(other.provides)
        self.conflicts.update(other.conflicts)
        self.replaces.update(other.replaces)

        self.depends.update(other.depends)
        self.make_depends.update(other.make_depends)
        self.check_depends.update(other.check_depends)
        self.opt_depends.update(other.opt_depends)

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

