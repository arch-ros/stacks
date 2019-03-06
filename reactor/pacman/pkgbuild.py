import subprocess

from ..package import Dependency, Version, Package

PKGBUILD_PROPERTIES = ['pkgname', 'pkgver', 'pkgrel','epoch', 'pkgdesc']
PKGBUILD_PROP_ARRAYS = ['arch', 'groups',
                        'depends','optdepends','makedepends','checkdepends',
                        'provides','conflicts','replaces']

""" Represents a PKGBUILD file and has utilities for extracting information
    like the package version, name, etc. """
class PkgBuild:
    _file_path = None

    def __init__(self, file_path):
        self._file_path = file_path

    @property
    def package_info(self):
        cmd = "source {} > /dev/null".format(self._file_path);
        for prop in PKGBUILD_PROPERTIES:
            cmd = cmd + " && echo ${}".format(prop)
        # Now read the arrays
        for prop in PKGBUILD_PROP_ARRAYS:
            cmd = cmd + " && echo ${{#{0}[@]}}; for index in ${{!{0}[@]}}; do echo ${{{0}[index]}}; done".format(prop)
        # Execute a process that retrieves the information
        proc = subprocess.Popen(cmd, shell=True, executable='/bin/bash', stdout=subprocess.PIPE)
        # Read the last lines
        lines = []
        for line in proc.stdout:
            lines.append(line.decode('utf-8').strip())

        props = {}
        for p,v in zip(PKGBUILD_PROPERTIES, lines):
            props[p] = v

        lines = lines[len(PKGBUILD_PROPERTIES):]
        for p in PKGBUILD_PROP_ARRAYS:
            length = int(lines.pop(0))
            array = lines[:length]
            lines = lines[length:]
            props[p] = array

        if len(props['pkgname']) <= 0:
            return None

        return Package('pacman',
                       name=props['pkgname'],
                       description=props['pkgdesc'],
                       version=Version.parse(props['pkgver'], 
                                             props['pkgrel'],  
                                             int(props['epoch']) if len(props['epoch']) > 0 else None),
                       arch=props['arch'],
                       groups=props['groups'],
                       depends=[Dependency.parse(x) for x in props['depends']],
                       make_depends=[Dependency.parse(x) for x in props['makedepends']],
                       check_depends=[Dependency.parse(x) for x in props['checkdepends']],
                       opt_depends=[Dependency.parse(x) for x in props['optdepends']],
                       provides=[Dependency.parse(x) for x in props['provides']],
                       conflicts=[Dependency.parse(x) for x in props['conflicts']],
                       replaces=[Dependency.parse(x) for x in props['replaces']],
                       artifacts={})
