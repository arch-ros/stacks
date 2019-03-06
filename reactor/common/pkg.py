import re
import numbers

def create_database():
    # A database consists of a hashmap from package hashes to package info and hashes to artifacts
    return {}

def db_add_package(db, pkg):
    db[pkginfo_hash(pkg['info'])] = pkg

# Merges a source into a dest,
# returning a map from package hash to
# status change (added, removed, modified)
def db_diff_merge(dbsrc, dbdest):
    diffs = {}
    for key,val in dbsrc.items():
        if key in dbdest and not val == dbdest[key]:
            # We have a modified package
            diffs[key] = 'modified'
            dbdest[key] = val
        elif not key in dbdest:
            # We have a new package
            diffs[key] = 'added'
            dbdest[key] = val
    # Remove any packages that have disappeared
    for key in dbdest:
        if not key in dbsrc:
            diffs[key] = 'removed'
            del dbdest[key]
    return diffs

# Query is a list of package infos, where
# the package infos contain regexes in their fields
def db_query(db, query):
    results = {}
    for h,pkg in db.items():
        if all(pkginfo_query_match(q, pkg) for q in query):
            results[h] = pkg

    return results

def create_pkgentry(info):
    return {'info': info, 'artifacts':[]}

def pkgentry_add_artifact(pkg, artifact):
    pkg['artifacts'].append(artifact)

def pkginfo_query_match(query_info, info):
    for key, val in query_info.items():
        if not key in info or type(info[key]) is not type(val):
            return False
        tgt = info[key]
        if isinstance(val, str) and not re.search(val, tgt):
            return False
        elif isinstance(val, numbers.Number) and val != tgt:
            return False
        elif isinstance(val, (list, tuple)) and not set(val).issubset(set(tgt)):
            return False
        elif isinstance(val, dict):
            return pkginfo_query_match(val, tgt)
    return True


def pkginfo_hash(pkginfo):
    return pkginfo['name'] + ' ' + version_string(pkginfo['version']) + ' ' + '/'.join(pkginfo['arch'])

def parse_version(pkgver, pkgrel = None, epoch = None):
    version = (pkgver.split(':')[1] if ':' in pkgver else pkgver).split('-')[0].split('.')
    epoch_num = epoch if epoch is not None else (int(pkgver.split(':')[0]) if ':' in pkgver else 0)
    release = pkgrel.split('.') if pkgrel is not None else (pkgver.split('-')[1].split('.') if '-' in pkgver else [])

    return {'version':version, 'release':release, 'epoch':epoch_num}


def version_string(version):
    v = '.'.join(version['version'])
    if len(version['release']) > 0:
        v = v + '-' + '.'.join(version['release'])
    if version['epoch'] > 0:
        v = str(version['epoch']) + ':' + v
    return v
