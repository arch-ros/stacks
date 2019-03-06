import zmq

import os
import json
import traceback

import pycman
import pyalpm

from reactor.pacman.pkgbuild import PkgBuild
import reactor.common.pkg as pkgformat

class RepoServer:
    _query_rep = None # query reply socket
    _update_pub = None # update publisher socket

    _pacman_conf = None
    _pacman_handle = None

    _db = None

    def __init__(self):
        self._db = pkgformat.create_database()

    def query(self, query):
        # Payload is the query list
        results = pkgformat.db_query(self._db, query)
        return results

    def sync_database(self):
        for db in self._pacman_handle.get_syncdbs():
            db.update(True)

        # Read the package list
        new_db = pkgformat.create_database()

        for db in self._pacman_handle.get_syncdbs():
            packages = db.search('')
            for pkg in packages:
                # Construct a package-info from the package
                info = {'name':pkg.name,'version':pkgformat.parse_version(pkg.version),
                        'arch':[pkg.arch],'groups':pkg.groups,'depends':pkg.depends,
                        'opt_depends':pkg.optdepends, 'build_depends':[],'conflicts':pkg.conflicts,
                        'provides':pkg.provides, 'replaces':pkg.replaces }

                pkgentry = pkgformat.create_pkgentry(info)
                pkgformat.db_add_package(new_db, pkgentry)


        # Calculate the diffs
        diffs = pkgformat.db_diff_merge(new_db, self._db)
        return diffs

    def run(self, context, config):
        # Get the config...
        self._pacman_conf = config['pacman_config']
        self._pacman_handle = pycman.config.PacmanConfig(conf=self._pacman_conf).initialize_alpm()

        self.sync_database()

        self._query_rep = context.socket(zmq.REP)
        self._update_pub = context.socket(zmq.PUB)

        # Bind...
        self._query_rep.bind(config['query_reply_bind'])
        self._update_pub.bind(config['update_pub_bind'])

        # Create a poller
        poller = zmq.Poller()
        poller.register(self._query_rep)

        timeout = config['check_interval']

        while True:
            try:
                socks = dict(poller.poll(timeout))
            except KeyboardInterrupt:
                break

            if self._query_rep in socks:
                query = json.loads(self._query_rep.recv_json());

                results = self.query(query['payload'])
                
                json_results = json.dumps(results)
                self._query_rep.send_json(json_results)
            else:
                diffs = self.sync_database()
                if len(diffs) > 0:
                    # Publish updates
                    json_updates = json.dumps(diffs)
                    self._update_pub.send_json(json_updates)
