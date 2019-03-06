import zmq

import os
import json
import traceback

from reactor.pacman.pkgbuild import PkgBuild
import reactor.common.pkg as pkgformat

class SrcDirServer:
    _query_rep = None # query reply socket
    _update_pub = None # update publisher socket

    _directory = None

    _db = None

    def __init__(self):
        self._db = pkgformat.create_database()

    def query(self, query):
        payload = query['payload']
        # Payload is the query list
        results = pkgformat.db_query(self._db, payload)
        return results

    def scan_diffs(self):
        # Read all the package infos
        new_db = pkgformat.create_database()

        files = os.listdir(self._directory)
        for f in files:
            fp = os.path.join(self._directory, f)
            buildfile = os.path.join(fp, 'PKGBUILD')
            if os.path.isdir(fp) and os.path.isfile(buildfile):
                # We found a valid build directory!
                # read the package info
                try:
                    pkgbuild = PkgBuild(buildfile)
                    pkgbuild_info = pkgbuild.info

                    pkg = pkgformat.create_pkgentry(pkgbuild.info)
                    pkgformat.db_add_package(new_db, pkg)
                except Exception as e:
                    print('Error {}'.format(traceback.format_exc()))

        diffs = pkgformat.db_diff_merge(new_db, self._db)
        return diffs


    def run(self, context, config):
        # Get the config...
        self._directory = config['directory']

        self._query_rep = context.socket(zmq.REP)
        self._update_pub = context.socket(zmq.PUB)

        # Bind...
        self._query_rep.bind(config['query_reply_bind'])
        self._update_pub.bind(config['update_pub_bind'])

        # Create a poller
        poller = zmq.Poller()
        poller.register(self._query_rep)

        timeout = config['check_interval']

        self.scan_diffs()
        while True:
            try:
                socks = dict(poller.poll(timeout))
            except KeyboardInterrupt:
                break

            if self._query_rep in socks:
                query = json.loads(self._query_rep.recv_json());

                results = self.query(query)
                
                json_results = json.dumps(results)
                self._query_rep.send_json(json_results)
            else:
                diffs = self.scan_diffs()
                if len(diffs) > 0:
                    # Publish updates
                    json_updates = json.dumps(diffs)
                    self._update_pub.send_json(json_updates)
