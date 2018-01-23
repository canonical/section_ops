#!/usr/bin/env python3

import os
import json
import logging

import requests


logging.basicConfig(format='%(asctime)s %(levelname)-5.5s %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

name_cache = {}


def get_snap_id(name):
    if name_cache.get(name) is not None:
        return name_cache[name]['snap_id']

    logger.info('Resolving {} ...'.format(name))
    headers = {
        'X-Ubuntu-Series': '16',
    }
    url = 'https://api.snapcraft.io/api/v1/snaps/details/{}'.format(name)
    r = requests.get(url, headers=headers)

    snap_id = r.json()['snap_id']
    name_cache.setdefault(name, {})['snap_id'] = snap_id

    return snap_id


def main():
    payload = {'sections': []}
    for fn in os.listdir('.'):
        if not fn.endswith('.section'):
            continue
        section_name = fn.split('.')[0]
        names = [n.strip() for n in open(fn).readlines() if n.strip()]

        logger.info(
            '=> Processing {} ({} entries)'
            .format(section_name, len(names)))

        snaps = []
        for i, n in enumerate(names):
            if n.startswith('#'):
                logger.warning('*** Ignoring {}'.format(n))
                continue
            snap = {
                'series': '16',
                'snap_id': get_snap_id(n),
                'featured': i < 2,
                'score': len(names) - i,
            }
            snaps.append(snap)
        payload['sections'].append({
            'section_name': section_name,
            'snaps': snaps,
        })

    logger.info('Saving "payload.json"')
    with open('payload.json', 'w') as fd:
        fd.write(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == '__main__':
    try:
        logger.info('Loading cache ...')
        with open('cache.json') as fd:
            name_cache = json.load(fd)
    except:
        logger.warning('No cache ...')

    try:
        main()
        logger.info(40 * '=')
        logger.info('Copy "payload.json" to a snapfind instance.')
        logger.info('Then run the following command:')
        logger.info(40 * '-')
        logger.info("curl -X POST -H 'Content-Type: application/json' "
                    "http://localhost:8003/sections/snaps -d '@payload.json'")
        logger.info(40 * '=')
    finally:
        logger.info('Saving cache ...')
        with open('cache.json', 'w') as fd:
            fd.write(json.dumps(name_cache, indent=2, sort_keys=True))
