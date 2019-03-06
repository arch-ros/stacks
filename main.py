import os
import zmq
import threading

from logbook import Logger, StreamHandler
import sys

StreamHandler(sys.stdout).push_application()

from reactor.pacman.repository import *
from reactor.builder import *
from reactor.chroot import *



# For built repository

arch_repo = BinaryDatabase('archlinux-bin', '/home/reactor/pacman-repo/pacman.conf')


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

# Create a build queue
builders = [ChrootBuilder('worker1', '/home/reactor/chroots/worker1',
                                     '/home/reactor/chroots/mkarchroot',
                                     '/home/reactor/chroots/makechrootpkg')]

queue = BuildQueue(arch_repo, aur_source, builders)

# Figure out what should be in the queue
queue.update_queue()
queue.run_jobs() # Assign free things in the build queue to jobs

"""
from reactor.pacman.srcdir_server import SrcDirServer
from reactor.pacman.repo_server import RepoServer
from reactor.terminal.terminal import Terminal

CONFIG = {
    'src_server' : {
        'query_reply_bind':'inproc://src_query',
        'update_pub_bind':'inproc://src_update',
        'directory': '/home/daniel/software/arch-ros-stacks/jade',
        'check_interval': 100000
    },
    'repo_server' : {
        'query_reply_bind':'inproc://repo_query',
        'update_pub_bind':'inproc://repo_update',

        'pacman_config': '/home/reactor/pacman-conf/pacman.conf',
        'check_interval': 100000
    },
    'terminal' : {
        'sockets': {
            'connect:REQ:query':'inproc://repo_query'
        }
    }
}

context = zmq.Context()

#src_server = SrcDirServer()
#src_server_thread = threading.Thread(target=src_server.run,args=(context, CONFIG['src_server']))
#src_server_thread.start()

repo_server = RepoServer()
repo_server_thread = threading.Thread(target=repo_server.run,args=(context, CONFIG['repo_server']))
repo_server_thread.start()

terminal = Terminal()
terminal.run(context, CONFIG['terminal'])
"""
