#!/usr/bin/env python3
"""See README.md for usage"""

import argparse
import glob
import json
import logging
import os
from collections import defaultdict

import requests

# Categories that do not allow self-serving.
CATEGORIES_TO_UPDATE = ("featured",)

# Number of entries (snaps) marked as "featured" within each section.
N_FEATURED = 20

STAGING_API_HOST = "api.staging.charmhub.io"
PROD_API_HOST = "api.charmhub.io"

logging.basicConfig(format="%(asctime)s %(levelname)s  %(message)s")
logging.addLevelName(logging.WARNING, "\033[1;93mWARN\033[0m")
logging.addLevelName(logging.ERROR, "\033[1;91mERRO\033[0m")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def parse_cmdline_args():
    parser = argparse.ArgumentParser(
        description="Section Operations", allow_abbrev=False,
    )
    parser.add_argument("--staging", action="store_true")
    parser.add_argument(
        "--quiet",
        action="store_const",
        const=logging.WARNING,
        default=logging.INFO,
        dest="log_level",
    )
    return parser.parse_args()


def get_section_dir(staging):
    return "staging" if staging else "prod"


def get_filename(prefix, staging):
    return "{}/{}-charms.json".format(get_section_dir(staging), prefix)


def get_api_host(staging):
    """If 'staging' is truthy, return staging API host instead of prod."""
    return STAGING_API_HOST if staging else PROD_API_HOST


def get_charm_id(staging, name, name_cache):
    """If 'staging' is truthy, request from staging instead of prod."""
    if name_cache.get(name) is not None:
        return name_cache[name]["id"]

    logger.info("Resolving {} ...".format(name))
    url = "https://{}/v2/charms/info/{}".format(get_api_host(staging), name)
    r = requests.get(url)

    charm_id = r.json()["id"]
    name_cache.setdefault(name, {})["id"] = charm_id

    return charm_id


def get_section_charms(staging, section_name):
    """If 'staging' is truthy, request from staging instead of prod."""
    url = "https://{}/v2/charms/find?category={}".format(
        get_api_host(staging), section_name
    )
    r = requests.get(url)
    r.raise_for_status()
    return r.json()['results']


def process_sections(args, name_cache):
    sections_by_name = defaultdict(list)

    for name in CATEGORIES_TO_UPDATE:
        logger.info("Fetching charms for: %s", name)
        section_charms = get_section_charms(args.staging, name)
        logger.info("%d charms.", len(section_charms))
        for charm in section_charms:
            sections_by_name[name].append(charm)

    current_sections = {
        section_name: [s["id"] for s in snaps]
        for section_name, snaps in sections_by_name.items()
    }

    logger.info("Processing new sections ...")
    new_sections = {}

    for fn in glob.glob(
        "{}/*.charm.section".format(get_section_dir(args.staging))
    ):
        # Get the "file" part of "dir/file.ext"
        section_name = fn.split("/")[1].split(".")[0]
        names = [n.strip() for n in open(fn).readlines() if n.strip()]
        unique_names = set(names)
        logger.info(
            "*** Parsing {} ({} entries)".format(
                section_name, len(unique_names)
            )
        )
        if len(unique_names) < len(names):
            logger.warning("!!! Ignoring duplicated entries.")
        charm_ids = []
        for name in names:
            if name.startswith("#"):
                logger.info("!!! Ignoring {}".format(name))
                continue
            try:
                charm_id = get_charm_id(args.staging, name, name_cache)
            except KeyError as err:
                logger.warning(
                    "!!! From '{}', charm '{}' not in store.".format(fn, name)
                )
                continue
            if charm_id in charm_ids:
                continue
            charm_ids.append(charm_id)
        new_sections[section_name] = charm_ids

    logger.info("Calculating updates ...")
    update_payload = {"sections": []}
    for section_name in sorted(new_sections.keys()):
        charm_ids = new_sections[section_name]
        charms = []
        for i, charm_id in enumerate(charm_ids):
            charm = {
                "snap_id": charm_id,
                "featured": False,
                # Keep the desired order, even if unfeatured.
                "score": len(charm_ids) - i,
            }
            charms.append(charm)

        update_payload["sections"].append(
            {"section_name": section_name, "snaps": charms}
        )

    logger.info('Saving "update-charms.json" ...')
    with open("update-charms.json", "w") as fd:
        fd.write(json.dumps(update_payload, indent=2, sort_keys=True))
    outputs = ["update-charms.json"]

    # Assemble deletion payload.
    logger.info("Calculating deletions ...")
    delete_sections = []
    delete_payload = {"sections": []}
    for section_name in sorted(current_sections.keys()):
        if section_name not in new_sections.keys():
            delete_sections.append(section_name)
            continue
        charm_ids = list(
            set(current_sections[section_name])
            - set(new_sections[section_name])
        )
        if not charm_ids:
            continue
        delete_payload["sections"].append(
            {
                "section_name": section_name,
                "snaps": [{"snap_id": s} for s in sorted(charm_ids)],
            }
        )

    if delete_payload["sections"]:
        logger.info('Saving "delete-charms.json" ...')
        with open("delete-charms.json", "w") as fd:
            fd.write(json.dumps(delete_payload, indent=2, sort_keys=True))
        outputs.append("delete-charms.json")
    else:
        logger.info("No deletions needed.")
        try:
            os.remove("delete-charms.json")
        except OSError:
            pass

    print(72 * "=")
    print(
        "Copy {} to a snapfind instance, then run:".format(
            " & ".join(repr(o) for o in outputs)
        )
    )
    print()
    if delete_payload["sections"]:
        print(
            "  $ curl -X DELETE -H 'Content-Type: application/json' "
            "http://localhost:8003/sections/snaps?namespace=charm -d "
            "'@delete-charms.json'"
        )
    print(
        "  $ curl -X POST -H 'Content-Type: application/json' "
        "http://localhost:8003/sections/snaps?namespace=charm -d "
        "'@update-charms.json'"
    )
    print()
    print(72 * "=")


def main():
    args = parse_cmdline_args()

    logger.setLevel(args.log_level)

    name_cache = {}
    try:
        logger.info("Loading cache ...")
        with open(get_filename("cache", args.staging)) as fd:
            name_cache = json.load(fd)
    except FileNotFoundError:
        logger.warning("Missing/Cold cache ...")

    try:
        process_sections(args, name_cache)
    finally:
        logger.info("Saving cache ...")
        with open(get_filename("cache", args.staging), "w") as fd:
            fd.write(json.dumps(name_cache, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
