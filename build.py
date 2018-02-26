#!/usr/bin/env python3


import argparse
import os
import json
import logging

import requests


logging.basicConfig(format='%(asctime)s %(levelname)-5.5s %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

name_cache = {}


# Both API calls only consider 'amd64' for now ...


def get_current_sections():
    r = requests.get('https://api.snapcraft.io/api/v1/snaps/sections')
    section_names = [
        s['name'] for s in r.json()['_embedded']['clickindex:sections']]
    sections = {}
    for name in section_names:
        r = requests.get(
            'https://api.snapcraft.io/api/v1/snaps/search'
            '?confinement=classic,strict&section={}&fields=snap_id'
            .format(name))
        snap_ids = [
            s['snap_id'] for s in r.json()['_embedded']['clickindex:package']]
        logger.info('+++ Fetched {} ({} entries)'.format(name, len(snap_ids)))
        sections[name] = snap_ids

    return sections


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
    parser = argparse.ArgumentParser(
        description='Section Operations ...'
    )
    parser.add_argument('-c', '--current', metavar='CURRENT.JSON',
                        help='Patch to existing current.json')
    args = parser.parse_args()

    if args.current:
        logger.info('Trying to load current section ...')
        try:
            with open(args.current) as fd:
                payload = json.load(fd)
                current_sections = {
                    item['section_name']: [s['snap_id'] for s in item['snaps']]
                    for item in payload['sections']}
        except FileNotFoundError:
            logger.error('Could not open {!r}'.format(args.current))
            return
        except json.decoder.JSONDecodeError:
            logger.error('Could not parse {!r}'.format(args.current))
            return
    else:
        logger.info('Fetching current sections ...')
        current_sections = get_current_sections()
        current_payload = {'sections': []}
        for section_name in sorted(current_sections.keys()):
            snap_ids = current_sections[section_name]
            snaps = []
            for i, snap_id in enumerate(snap_ids):
                snap = {
                    'series': '16',
                    'snap_id': snap_id,
                    'featured': i < 20,
                    'score': len(snap_ids) - i,
                }
                snaps.append(snap)
            current_payload['sections'].append({
                'section_name': section_name,
                'snaps': snaps,
            })

        logger.info('Saving "current.json" ¯\_(ツ)_/¯ ...')
        with open('current.json', 'w') as fd:
            fd.write(json.dumps(current_payload, indent=2, sort_keys=True))

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

    # Assembly deletion payload.
    logger.info('Calculating snap deletions ...')
    delete_sections = []
    delete_payload = {'sections': []}
    for section_name in sorted(current_sections.keys()):
        if section_name not in new_sections.keys():
            delete_sections.append(section_name)
            continue
        snap_ids = list(
            set(current_sections[section_name]) -
            set(new_sections[section_name]))
        if not snap_ids:
            continue
        delete_payload['sections'].append({
            'section_name': section_name,
            'snaps': [
                {'series': '16', 'snap_id': s} for s in sorted(snap_ids)],
        })

    logger.info('Saving "delete.json" ...')
    with open('delete.json', 'w') as fd:
        fd.write(json.dumps(delete_payload, indent=2, sort_keys=True))

    logger.info('Calculating snap updates ...')
    update_payload = {'sections': []}
    for section_name in sorted(new_sections.keys()):
        snap_ids = new_sections[section_name]
        snaps = []
        for i, snap_id in enumerate(snap_ids):
            snap = {
                'series': '16',
                'snap_id': snap_id,
                'featured': i < 20,
                'score': len(snap_ids) - i,
            }
            snaps.append(snap)
        update_payload['sections'].append({
            'section_name': section_name,
            'snaps': snaps,
        })

    logger.info('Saving "update.json" ...')
    with open('update.json', 'w') as fd:
        fd.write(json.dumps(update_payload, indent=2, sort_keys=True))

    print(72 * '=')
    print('Copy "delete.json" and "update.json" to a snapfind instance. '
          'Then run the following commands:')
    print()
    print("  $ curl -X DELETE -H 'Content-Type: application/json' "
          "http://localhost:8003/sections/snaps -d '@delete.json'")
    print("  $ curl -X POST -H 'Content-Type: application/json' "
          "http://localhost:8003/sections/snaps -d '@update.json'")
    if delete_sections:
        print('  $ psql <production_dsn> -c "DELETE FROM section WHERE '
              'name IN ({});"'
              .format(', '.join([repr(s) for s in delete_sections])))
    print()
    print('In case you screwed things up, copy "current.json" to a snapfind '
          'instance. Then run the following commands:')
    print()
    print('  $ psql <production_dsn> -c "DELETE FROM section;"')
    print("  $ curl -X POST -H 'Content-Type: application/json' "
          "http://localhost:8003/sections/snaps -d '@current.json'")
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
