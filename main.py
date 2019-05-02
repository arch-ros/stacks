import os
import threading
import asyncio
import time
import atexit

from aiohttp import web

from logbook import Logger, StreamHandler
import sys

StreamHandler(sys.stdout).push_application()

from oyster.pacman.repository import *
from oyster.pacman.database import *
from oyster.pacman.chroot import *
from oyster.events import *
from oyster.database import *
from oyster.job import *

def create_arch_source_repo():
    # For archlinux source repository
    def update_fs(db, directory):
        return False

    def find_package_dirs(db, directory):
        dirs = []
        for f in os.listdir(directory):
            paths = ['core-x86_64', 'core-any', 'extra-x86_64', 'extra-any']
            for p in paths:
                path = os.path.join(directory, f, 'repos', p)
                pkgbuild_path= os.path.join(path, 'PKGBUILD')
                if os.path.isdir(path) and os.path.isfile(pkgbuild_path):
                    dirs.append(path)
        return dirs

    return SourceDatabase('archlinux-source', '/home/oyster/packages/archlinux', find_package_dirs)

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

    return SourceDatabase('ros-source', '/home/oyster/packages/ros', find_package_dirs)

async def main():
    logger = Logger('main')

    # repository to push to
    pearl_repo = Repository('/repo/pearl/packages', '/repo/pearl/pearl.db.tar.xz')

    # The pearl packages
    pearl_bin = BinaryDatabase('pearl', '/repo/pearl/packages')
    # The arch linux packages, updated only at start
    arch_bin = RemoteDatabase('arch', '/home/oyster/arch-repo/pacman.conf', True)
    combined_bin = DerivedDatabase('binaries', [pearl_bin, arch_bin])
    combined_bin.update()


    # Combined source repository
    pearl_src = DerivedDatabase('source', [create_ros_database()])

    # Create a build queue
    workers = [ChrootWorker('worker1', '/home/oyster/chroots/worker1',
                                         '/home/oyster/chroots/pacman.conf',
                                         '/repo/pearl/packages',
                                         '/home/oyster/chroots/mkarchroot',
                                         '/home/oyster/chroots/makechrootpkg')]
    event_log = EventLog()

    event_log.load('/home/oyster/history.json')
    atexit.register(lambda: event_log.save('/home/oyster/history.json'))

    scheduler = Scheduler(pearl_bin, pearl_src, dependency_resolver=combined_bin)

    async def handle_result(job, build):
        if build.status == BuildStatus.FAILURE:
            scheduler.schedule(Reschedule(job, 3600))
        if build.status == BuildStatus.SUCCESS:
            for f in build.artifacts['binary_files']:
                await pearl_repo.add(f, logger=build.logger)

    for w in workers:
        w.add_listener(handle_result)

    await asyncio.gather(run_website(scheduler, event_log, workers, [ pearl_bin, pearl_src ]),
                         run_scheduler(scheduler, event_log, workers))

async def run_scheduler(scheduler, build_log, workers):
    await scheduler.run(build_log, workers)

async def run_website(scheduler, build_log, workers, databases):
    import oyster.web

    app = oyster.web.make_app(scheduler, build_log, workers, databases)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_forever()
