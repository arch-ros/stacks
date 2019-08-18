import subprocess
import os
import regex

from ..package import Dependency, Version, Package

PKGBUILD_PROP_VALUES = ['pkgbase', 'pkgver', 'pkgrel','epoch', 'pkgdesc']
PKGBUILD_PROP_ARRAYS = ['arch', 'groups', 'pkgname',
                        'depends','optdepends','makedepends','checkdepends',
                        'provides','conflicts','replaces']
PKGBUILD_PROPS = PKGBUILD_PROP_VALUES + PKGBUILD_PROP_ARRAYS

def _extract_props(source):
    cmd = source
    for prop in PKGBUILD_PROP_VALUES:
        cmd = cmd + "\n echo ${}".format(prop)
    # Now read the arrays
    for prop in PKGBUILD_PROP_ARRAYS:
        cmd = cmd + "\n echo ${{#{0}[@]}}; for index in ${{!{0}[@]}}; do echo ${{{0}[index]}}; done".format(prop)
    # Execute a process that retrieves the information
    proc = subprocess.Popen(cmd, shell=True, executable='/bin/bash', stdout=subprocess.PIPE)
    # Read the last lines
    lines = []
    for line in proc.stdout:
        lines.append(line.decode('utf-8').strip())

    props = {}
    for p,v in zip(PKGBUILD_PROP_VALUES, lines):
        props[p] = v

    lines = lines[len(PKGBUILD_PROP_VALUES):]
    for p in PKGBUILD_PROP_ARRAYS:
        length = int(lines.pop(0))
        array = lines[:length]
        lines = lines[length:]
        props[p] = array
    return props

def _make_pkg(name, base, props):
    return Package('pacman',
                   parent=base if base else name,
                   name=name,
                   description=props['pkgdesc'],
                   version=Version.parse(props['pkgver'], 
                                         props['pkgrel'],  
                                         int(props['epoch']) if len(props['epoch']) > 0 else None),
                   arch=set(props['arch']),
                   groups=set(props['groups']),
                   depends={Dependency.parse(x) for x in props['depends']},
                   make_depends={Dependency.parse(x) for x in props['makedepends']},
                   check_depends={Dependency.parse(x) for x in props['checkdepends']},
                   opt_depends={Dependency.parse(x) for x in props['optdepends']},
                   provides={Dependency.parse(x) for x in props['provides']},
                   conflicts={Dependency.parse(x) for x in props['conflicts']},
                   replaces={Dependency.parse(x) for x in props['replaces']},
                   artifacts={})

def _extract_function(source, funcname):
    prefix = funcname + '\(\)\s+'
    result = regex.search(prefix + r'''
        (?<rec> #capturing group rec
         \{ #open parenthesis
         (?<cont>
         (?: #non-capturing group
          [^{}]++ #anyting but parenthesis one or more times without backtracking
          | #or
           (?&rec) #recursive substitute of group rec
         )*
         )
         \} #close parenthesis
        )''',source,flags=regex.VERBOSE | regex.MULTILINE)
    if not result:
        return None
    else:
        return result.group(2)

def _extract_proplines(source):
    reg = '(\[\[[^\[\]\n]*\]\])|(' + \
            '|'.join(map(lambda prop: '(?:' + prop + '\s*=\s*\([^\(\)]*\))|' + \
                                      '(?:' + prop + '\s*=.*\n)',
                        PKGBUILD_PROPS)) \
              + ')'
    it = regex.finditer(reg, source)
    return '\n'.join(filter(lambda s: not s.startswith('[['), # remove [[ ]] answers
                        map(lambda m: m.group(0).strip(), it)))

""" Represents a PKGBUILD file and has utilities for extracting information
    like the package version, name, etc. """
class PkgBuild:
    _file_path = None

    def __init__(self, file_path):
        self._file_path = file_path


    @property
    def packages(self):
        if not os.path.exists(self._file_path):
            raise IOError('Unable to find file {}'.format(self._file_path))

        pkgs = []
        with open(self._file_path) as f:
            lines = f.readlines()
        source = ''.join(lines)
        props = _extract_props(source)
        if len(props['pkgname']) <= 0:
            return None
        if len(props['pkgbase']) <= 0:
            for n in props['pkgname']:
                pkgs.append(_make_pkg(n, None, props))
        else:
            pkgbase = props['pkgbase']
            # re-run with the package functions
            for n in props['pkgname']:
                func_text = _extract_function(source, 'package_' + n)
                if not func_text and n.startswith(pkgbase):
                    func_text = _extract_function(source, 'package' + n[len(pkgbase):])
                if not func_text:
                    raise IOError('Unable to find section for {}'.format(n))
                prop_source = _extract_proplines(func_text)

                sub_props = _extract_props(source + '\n' + prop_source)
                pkgs.append(_make_pkg(n, props['pkgbase'], sub_props))
        return pkgs
