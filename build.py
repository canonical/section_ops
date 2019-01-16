#!/usr/bin/env python3


import argparse
import os
import itertools
import json
import logging
import sys
import time

import requests

# Categories that do not allow self-serving.
EXCLUSIVE_CATEGORIES = (
    'featured',
    'ubuntu-firstrun',
)

# Number of entries (snaps) marked as "featured" within each section.
N_FEATURED = 20


logging.basicConfig(format='%(asctime)s %(levelname)-4.4s  %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

name_cache = {}


def get_snap_id(name):
    if name_cache.get(name) is not None:
        return name_cache[name]['snap_id']

    logger.info('Resolving {} ...'.format(name))
    headers = {
        'Snap-Device-Series': '16',
    }
    url = 'https://api.snapcraft.io/v2/snaps/info/{}'.format(name)
    r = requests.get(url, headers=headers)

    snap_id = r.json()['snap-id']
    name_cache.setdefault(name, {})['snap_id'] = snap_id

    return snap_id


def get_snap_name(snap_id):
    id_cache = {v['snap_id']: k for k, v in name_cache.items()}
    if id_cache.get(snap_id) is not None:
        return id_cache[snap_id]

    url = ('https://api.snapcraft.io/api/v1/snaps/assertions/'
           'snap-declaration/16/{}'.format(snap_id))
    r = requests.get(url)

    name = r.json()['headers']['snap-name']
    name_cache.setdefault(name, {})['snap_id'] = snap_id

    return name


def get_promoted_snaps():
    snaps = []
    headers = {
        'X-Ubuntu-Series': '16',
    }

    url = (
        'https://api.snapcraft.io/api/v1/snaps/search'
        '?scope=wide&arch=wide&confinement=strict,classic,devmode&'
        'promoted=true&fields=snap_id,sections'
    )

    while url is not None:
        # ensure cache is busted when fetching promoted.
        cachebust= '&x=%s' % int(time.time())
        r = requests.get(url + cachebust, headers=headers)
        r.raise_for_status()
        payload = r.json()

        sys.stderr.write('.')
        sys.stderr.flush()
        snaps.extend(payload['_embedded']['clickindex:package'])

        _next = payload['_links'].get('next')
        url = _next['href'] if _next is not None else None

    sys.stderr.write('\n')
    sys.stderr.flush()
    return snaps


def main():
    parser = argparse.ArgumentParser(
        description='Section Operations ...'
    )
    args = parser.parse_args()

    logger.info('Fetching all currently promoted snaps.')
    promoted = get_promoted_snaps()
    logger.info('Fetched %d snaps.', len(promoted))
    sections_by_name = {}
    for snap in promoted:
        for section in snap['sections']:
            name = section['name']
            snaps = sections_by_name.setdefault(name, [])
            snaps.append({
                'snap_id': snap['snap_id'],
                'featured': section['featured'],
            })
    # Cannot properly score results.
    current_sections = {
        section_name: [s['snap_id'] for s in snaps]
        for section_name, snaps in sections_by_name.items()}

    logger.info('Processing new sections ...')
    new_sections = {}
    for fn in os.listdir('.'):
        if not fn.endswith('.section'):
            continue
        section_name = fn.split('.')[0]
        names = [n.strip() for n in open(fn).readlines() if n.strip()]
        unique_names = set(names)
        logger.info(
            '*** Parsing {} ({} entries)'.format(section_name, len(unique_names)))
        if len(unique_names) < len(names):
            logger.warning('!!! Ignoring duplicated entries.')
        snap_ids = []
        for name in names:
            if name.startswith('#'):
                logger.info('!!! Ignoring {}'.format(name))
                continue
            snap_id = get_snap_id(name)
            if snap_id in snap_ids:
                continue
            snap_ids.append(snap_id)
        new_sections[section_name] = snap_ids

    logger.info('Calculating snap updates ...')
    update_payload = {'sections': []}
    for section_name in sorted(new_sections.keys()):
        # Build the 'featured-in-category' list.
        snap_ids = new_sections[section_name]
        snaps = []
        for i, snap_id in enumerate(snap_ids):
            featured = i < N_FEATURED
            snap = {
                'snap_id': snap_id,
                'featured': featured,
                'score': N_FEATURED - i if featured else 0,
            }
            snaps.append(snap)

        # If it is not an exclusive category (see the pruning below),
        # append the remaining snaps (self-served or un-featured).
        if section_name not in EXCLUSIVE_CATEGORIES:
            snap_ids = list(
                set(current_sections.get(section_name, [])) -
                set(new_sections.get(section_name, [])))
            for snap_id in snap_ids:
                snap = {
                    'snap_id': snap_id,
                    'featured': False,
                    'score': 0,
                }
                snaps.append(snap)

        update_payload['sections'].append({
            'section_name': section_name,
            'snaps': snaps,
        })

    logger.info('Saving "update.json" ...')
    with open('update.json', 'w') as fd:
        fd.write(json.dumps(update_payload, indent=2, sort_keys=True))

    # Assembly deletion payload.
    logger.info('Calculating snap deletions ...')
    delete_sections = []
    delete_payload = {'sections': []}
    for section_name in sorted(current_sections.keys()):
        if section_name not in new_sections.keys():
            delete_sections.append(section_name)
            continue
        # Only prune exclusive categories.
        if section_name not in EXCLUSIVE_CATEGORIES:
            continue
        snap_ids = list(
            set(current_sections[section_name]) -
            set(new_sections[section_name]))
        if not snap_ids:
            continue
        delete_payload['sections'].append({
            'section_name': section_name,
            'snaps': [{'snap_id': s} for s in sorted(snap_ids)],
        })

    if delete_payload['sections']:
        logger.info('Saving "delete.json" ...')
        with open('delete.json', 'w') as fd:
            fd.write(json.dumps(delete_payload, indent=2, sort_keys=True))
    else:
        logger.info('No deletions needed.')

    print(72 * '=')
    print('Copy "delete.json" and "update.json" to a snapfind instance. '
          'Then run the following commands:')
    print()
    if delete_payload['sections']:
        print("  $ curl -X DELETE -H 'Content-Type: application/json' "
              "http://localhost:8003/sections/snaps -d '@delete.json'")
    print("  $ curl -X POST -H 'Content-Type: application/json' "
          "http://localhost:8003/sections/snaps -d '@update.json'")

    if delete_sections:
        print('  $ psql <production_dsn> -c "DELETE FROM section WHERE '
              'name IN ({});"'
              .format(', '.join([repr(s) for s in delete_sections])))

        updated_snaps = []
        for section in update_payload['sections']:
            updated_snaps.extend(s['snap_id'] for s in section['snaps'])

        for n in delete_sections:
            dead_ids = [
                snap_id for snap_id in current_sections.get(n, [])
                if snap_id not in updated_snaps]
            if not dead_ids:
                continue
            print('  Orphan assignments from "{}":'.format(n))
            for s in dead_ids:
                print('  - {}'.format(get_snap_name(s)))
    print(72 * '=')


if __name__ == '__main__':
    try:
        logger.info('Loading cache ...')
        with open('cache.json') as fd:
            name_cache = json.load(fd)
    except:
        logger.warning('Missing/Cold cache ...')

    try:
        main()
    finally:
        logger.info('Saving cache ...')
        with open('cache.json', 'w') as fd:
            fd.write(json.dumps(name_cache, indent=2, sort_keys=True))
