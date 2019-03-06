

class Job:
    def __init__(self, builder, package):
        self.builder = builder
        self.package = package

class BuildQueue:
    def __init__(self, compiled_db, source_db, builder_pool):
        self._build_queue = []

    def update():
        for pkg in self.source_db:
            if not pkg in self.compiled_db and not pkg in self._build_queue:
                self._build_queue.append(pkg)

class Builder:

