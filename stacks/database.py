import threading
from enum import Enum
from .package import Dependency

class DiffType(Enum):
    ADDED = 'added'
    MODIFIED = 'modified'
    REMOVED = 'removed'

class MergeMode(Enum):
    REPLACE = 'replace'

class Diff:
    def __init__(self, type, old, new):
        self.type = type
        self.old = old
        self.new = new

class Database:
    def __init__(self, name='', packages=[]):
        self.name = name
        self._packages = {}
        self._provides = {}
        self._listeners = []

        if len(packages) > 0:
            for x in packages:
                self._add(x)

    # Getters

    # gets all packages with a particular name
    def find(self, requirement):
        return self._provides.get(requirement, [])

    def __iter__(self):
        for package in self._packages.values():
            yield package

    def __contains__(self, package):
        return package.identifier in self._packages

    def __len__(self):
        return len(self._packages)

    # for listeners

    def add_listener(self, l):
        self._listeners.append(l)

    def add_remove_listener(self, l):
        def c(diffs):
            for d in diffs:
                if d.type == DiffType.REMOVED:
                    l(d.old)
        self._listeners.append(c)

    def add_add_listener(self, l):
        def c(diffs):
            for d in diffs:
                if d.type == DiffType.ADDED:
                    l(d.new)
        self._listeners.append(c)

    def _changed(self, diffs):
        for l in self._listeners:
            l(diffs)

    # modifiers
    def _add(self, pkg):
        self._packages[pkg.identifier] = pkg
        for p in (pkg.provides | {Dependency(pkg.name)}):
            if not p in self._provides:
                self._provides[p.name] = []
            self._provides[p.name].append(pkg)

    def _remove(self, pkg):
        del self._packages[pkg.identifier]
        for p in (pkg.provides | {Dependency(pkg.name)}):
            if len(self._provides[p.name]) == 1:
                del self._provides[p.name]
            else:
                self._provides[p.name].remove(pkg)
    
    def add(self, pkg):
        if pkg not in self:
            self._add(pkg)
            self._changed([Diff(DiffType.ADDED, None, pkg)])

    def remove(self, pkg):
        if pkg in self:
            self._remove(pkg)
            self._changed([Diff(DiffType.REMOVED, pkg, None)])

    # Calculate the diffs to get from this db to odb
    def diffs(self, odb):
        diffs = []
        for pkg in self:
            if pkg not in odb:
                diffs.append(Diff(DiffType.REMOVED, pkg, None))
        for pkg in odb:
            if pkg not in self:
                diffs.append(Diff(DiffType.ADDED, None, pkg))
            else:
                our_package = self._packages[pkg.identifier].clone()
                their_package = pkg.clone()
                if our_package != pkg:
                    diffs.append(Diff(DiffType.MODIFIED, our_package, their_package))
        return diffs

    def process(self, diffs, merge_mode=MergeMode.REPLACE,
                    remove=True, add=True, merge=True, filter=None):
        applied = []
        for d in diffs:
            if d.type == DiffType.ADDED and add \
                    and (filter is None or filter(d.new)):

                self._add(d.new)
                applied.append(d)

            if d.type == DiffType.REMOVED and remove \
                    and (filter is None or filter(d.old)):
                self._remove(d.old)
                applied.append(d)

            if d.type == DiffType.MODIFIED and merge \
                    and (filter is None or filter(d.new)):

                if merge_mode == MergeMode.REPLACE:
                    self._packages[d.old.identifier].replace(d.new)
                    applied.append(d)
                else:
                    raise NotImplementedError('Unknown merge mode')

        self._changed(applied)
        return applied

    # Replaces this db with the other db
    # and returns the diffs needed to get there
    def replace(self, odb):
        diffs = self.diffs(odb) 
        return self.process(diffs, MergeMode.REPLACE)

    # Called to update the database
    # overridden by subtypes
    def update(self):
        pass

    def __str__(self):
        return '\n'.join([str(x) for x in self._packages.values()])

class DerivedDatabase(Database):
    def __init__(self, name, databases, filter=None):
        super().__init__(name)
        self._databases = databases
        self._filter = filter
        self._diffs = []
        self._diffs_lock = threading.Lock()

        def process(diffs):
            with self._diffs_lock:
                self._diffs.extend(diffs)
        
        for d in databases:
            self.process(self.diffs(d), MergeMode.REPLACE,
                            remove=False, add=True, merge=True,
                            filter=self._filter)
            d.add_listener(process)

    def update(self):
        for d in self._databases:
            d.update()

        # Process all the diffs
        with self._diffs_lock:
            self.process(self._diffs, MergeMode.REPLACE,
                            remove=False, add=True, merge=True,
                            filter=self._filter)
            self._diffs = []
