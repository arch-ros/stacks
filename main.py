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

async def main():
    logger = Logger('main')

    # repository to push to
    pearl_repo = Repository('/repo/pearl/packages', '/repo/pearl/pearl.db.tar.xz')

    pearl_bin = BinaryDatabase('pearl', '/repo/pearl/packages')

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

    arch_source = SourceDatabase('archlinux-source', '/home/oyster/packages/archlinux', find_package_dirs)

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

    aur_source = SourceDatabase('aur-source', '/home/oyster/packages/aur', find_package_dirs)

    # Combined source repository
    pearl_src = DerivedDatabase('source', [arch_source, aur_source])

    # when things are removed from the 
    # source repository, remove them from the pearl repository
    # TODO: This doesn't work if the version just changes
    # pearl_src.add_remove_listener(lambda p: pearl_repo.remove(p.name))

    # Create a build queue
    workers = [ChrootWorker('worker1', '/home/oyster/chroots/worker1',
                                         '/home/oyster/chroots/pacman.conf',
                                         '/repo/pearl/packages',
                                         '/home/oyster/chroots/mkarchroot',
                                         '/home/oyster/chroots/makechrootpkg')]
    event_log = EventLog()

    event_log.load('/home/oyster/history.json')
    atexit.register(lambda: event_log.save('/home/oyster/history.json'))

    scheduler = Scheduler(pearl_bin, pearl_src)

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
    #await run_website(scheduler, event_log, workers, [ pearl_bin, pearl_src ])

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
