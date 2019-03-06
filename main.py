import os
import zmq
import threading

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
