
import os
import threading
import asyncio
import time
import atexit

from aiohttp import web

from logbook import Logger, StreamHandler,FileHandler
import sys

if len(sys.argv) < 2:
    print('needs at least one argument')
    sys.exit(1)

RUNTIME_DIR = sys.argv[1]

StreamHandler(sys.stdout).push_application()
FileHandler(RUNTIME_DIR + '/log.txt', bubble=True).push_application()

from stacks.pacman.repository import *
from stacks.pacman.database import *
from stacks.pacman.chroot import *
from stacks.events import *
from stacks.database import *
from stacks.job import *


def create_ros_database():
    # For aur source repository
    def update_fs(db, directory):
        return False

    def find_package_dirs(db, directory):
        dirs = []
        for f in os.listdir(directory):
            path = os.path.join(directory, f)
            pkgbuild = os.path.join(path, 'PKGBUILD')
            if os.path.isdir(path) and os.path.exists(pkgbuild):
                dirs.append(path)
        return dirs

    return SourceDatabase('ros-source', RUNTIME_DIR + '/packages/ros', find_package_dirs)

def create_worker(name):
    return ChrootWorker(name, RUNTIME_DIR + '/chroots',
                               RUNTIME_DIR + '/config/pacman_chroots.conf',
                               RUNTIME_DIR + '/scripts/mkarchroot',
                               RUNTIME_DIR + '/scripts/makechrootpkg',
                               RUNTIME_DIR + '/scripts/updatechroot')

async def main():
    logger = Logger('main')

    # repository to push to
    push_repo = Repository('/repo/ros/x86_64', '/repo/ros/x86_64/ros.db.tar.xz')

    # The built packages repository
    built_packages = RemoteDatabase('built', RUNTIME_DIR + '/config/ros-repo/pacman.conf')
    # The arch linux packages, updated only at start
    arch_bin = RemoteDatabase('arch', RUNTIME_DIR + '/config/arch-repo/pacman.conf', True)

    # A combined database for dependency resolution
    dependencies = DerivedDatabase('dependencies', [built_packages, arch_bin])
    dependencies.update()

    # Combined source repository
    sources = create_ros_database()

    # Create a build queue
    workers = [create_worker('worker1'), create_worker('worker2')]
    event_log = EventLog()

    event_log.load(RUNTIME_DIR + '/history.json')
    atexit.register(lambda: event_log.save(RUNTIME_DIR + '/history.json'))

    scheduler = Scheduler(built_packages, sources, dependency_resolver=dependencies)

    async def handle_result(job, build):
        if build.status == BuildStatus.FAILURE:
            scheduler.schedule(Reschedule(job, 3600))
        if build.status == BuildStatus.SUCCESS:
            for f in build.artifacts['binary_files']:
                await push_repo.add(f, logger=build.logger)

    for w in workers:
        w.add_listener(handle_result)

    await asyncio.gather(run_website(scheduler, event_log, workers, [ built_packages, sources]),
                         run_scheduler(scheduler, event_log, workers))

async def run_scheduler(scheduler, build_log, workers):
    await scheduler.run(build_log, workers)

async def run_website(scheduler, build_log, workers, databases):
    import stacks.web

    app = stacks.web.make_app(scheduler, build_log, workers, databases)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_forever()
