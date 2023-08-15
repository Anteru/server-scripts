#!/usr/bin/env python3

# SPDX-License-Identifier: BSD-2-Clause


import zfs
import zfs.snapshot

import syslog
import argparse
import datetime
from contextlib import ContextDecorator
import subprocess

try:
    import tomllib as toml
except ImportError:
    import tomli as toml

__version__ = '1.0'


class syslog_context(ContextDecorator):
    def __init__(self, name):
        self.__name = name

    def __enter__(self):
        syslog.openlog(self.__name)

    def __exit__(self, exc_type, exc, exc_tb):
        syslog.closelog()


@syslog_context('zfs-snapshot')
def _snapshot(args):
    if args.config is not None:
        config = zfs.snapshot.ParseConfiguration(args.config)
    else:
        config = zfs.snapshot.GetDefaultConfiguration()

    for pool in zfs.GetPools():
        syslog.syslog(
            syslog.LOG_INFO,
            'Processing pool "{0}"'.format(pool))

        if pool in config:
            recursive = config[pool]['recursive']
            ignore = config[pool]['ignore']
        else:
            recursive = config['_default']['recursive']
            ignore = config['_default']['ignore']

        if ignore:
            syslog.syslog(syslog.LOG_INFO, f'Skipping pool "{pool}"')
            continue

        dt = datetime.datetime.utcnow()
        snapshot_name = dt.strftime('shadow_copy-%Y.%m.%d-%H.%M.%S')
        zfs.CreateSnapshot(pool, snapshot_name,
                           dryRun=args.dry_run,
                           recursive=recursive)

    for filesystem in zfs.GetFilesystems():
        snapshots = zfs.GetSnapshots(filesystem, prefix='shadow_copy')

        if filesystem in config:
            if config[filesystem]['ignore']:
                syslog.syslog(
                    syslog.LOG_INFO,
                    f'Skipping filesystem "{filesystem}"')
                continue
            _, obsoleteSnapshots = zfs.snapshot.FilterSnapshots(
                snapshots, filters=config[filesystem]['filters'])
        else:
            _, obsoleteSnapshots = zfs.snapshot.FilterSnapshots(
                snapshots, filters=config['_default']['filters'])

        for snapshot in obsoleteSnapshots:
            zfs.DestroySnapshot(
                snapshot.Path, snapshot.Name,
                recursive=False, dryRun=args.dry_run)


@syslog_context('zfs-backup')
def _backup(args):
    config = {
        'filesystems': ['tank/Default'],
        'backup-prefix': 'backup_'
    }

    if args.config:
        config = toml.load(args.config)

    for fs in config['filesystems']:
        for snapshot in zfs.GetSnapshots(fs, config['backup-prefix']):
            short_name = snapshot.Timestamp.strftime(
                config['backup-prefix'] + '%Y-%m-%d')

            # TODO: Check if a snapshot of this name already exists, if not
            # create one. If there's another snapshot with the same prefix,
            # assume it's a backup and turn this into an incremental send

            target_path = args.TARGET_POOL + '/' + \
                snapshot.Path.replace('/', '_')
            print(f"Creating backup of '{snapshot.Path}@{snapshot.Name}' to "
                  f"'{target_path}'")

            call = ['zfs', 'send', f"{snapshot.Path}@{snapshot.Name}",
                    '|',
                    'zfs', 'recv', '-Fuv', target_path
            ]

            if args.dry_run:
                print(' '.join(call))
            else:
                subprocess.call(' '.join(call), shell=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')

    subparsers = parser.add_subparsers(required=True)

    snapshot = subparsers.add_parser('snapshot')
    snapshot.add_argument('-c', '--config', type=argparse.FileType('rb'))
    snapshot.set_defaults(func=_snapshot)

    backup = subparsers.add_parser('backup')
    backup.add_argument('-c', '--config', type=argparse.FileType('rb'))
    backup.add_argument('TARGET_POOL')
    backup.set_defaults(func=_backup)

    args = parser.parse_args()

    args.func(args)
