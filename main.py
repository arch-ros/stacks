import os
import zmq
import threading

from logbook import Logger, StreamHandler
import sys

StreamHandler(sys.stdout).push_application()

from reactor.pacman.repository import *
from reactor.pacman.database import *
from reactor.database import *
from reactor.pacman.chroot import *
from reactor.builder import *

# For built repository
pearl_bin = BinaryDatabase('pearl-bin', '/home/reactor/pacman-repo/pacman.conf')
pearl_repo = Repository('pearl-repo', '/repo/pearl/packages', '/repo/pearl/pearl.db.tar.xz')


# For archlinux source repository
def update_fs(db, directory):
    return False

def find_package_dirs(db, directory):
    dirs = []
    for f in os.listdir(directory):
        src_x86_path = os.path.join(directory, f, 'repos', 'core-x86_64')
        pkgbuild_x86_path = os.path.join(src_x86_path, 'PKGBUILD')
        if os.path.isdir(src_x86_path) and os.path.exists(pkgbuild_x86_path):
            dirs.append(src_x86_path)
    return dirs

arch_source = SourceDatabase('archlinux-src', '/home/reactor/packages/archlinux', update_fs, find_package_dirs)

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

aur_source = SourceDatabase('aur-src', '/home/reactor/packages/aur', update_fs, find_package_dirs)

# Combined source repository
pearl_src = MergedDatabase('pearl-src', [arch_source, aur_source])



# Create a build queue
builders = [ChrootBuilder('worker1', '/home/reactor/chroots/worker1',
                                     '/home/reactor/chroots/mkarchroot',
                                     '/home/reactor/chroots/makechrootpkg')]

queue = BuildQueue('pacman_queue', pearl_bin, pearl_src, builders)

# After success, binary_file should be populated in chroot jobs' artifacts
queue.add_success_hook(lambda job: pearl_repo.add(job.artifacts['binary_file']))

# Whenever a package is removed from the source
# repository, remove it from the binary repository
pearl_src.add_remove_listener(lambda p: pearl_repo.remove(p.name))

# Figure out what should be in the queue
queue.update_queue()
queue.run_jobs() # Assign free things in the build queue to free workers that can take them
