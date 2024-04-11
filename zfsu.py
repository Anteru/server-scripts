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

    prefix = config['backup-prefix']

    for fs in config['filesystems']:
        # Create a new snapshot for the backup
        dt = datetime.datetime.now(datetime.UTC)
        snapshot_name = dt.strftime(f'{prefix}%Y-%m-%d')

        if snapshot := zfs.GetSnapshot(fs, snapshot_name):
            print(f'Reusing snapshot {snapshot.Path}@{snapshot.Name}')
        else:
            print(f'Creating snapshot {fs}@{snapshot_name}')
            # We didn't find a matching snapshot
            zfs.CreateSnapshot(fs, snapshot_name, recursive=False,
                               dryRun=args.dry_run)

        target_path = args.TARGET_POOL + '/' + fs.replace('/', '_')

        target_snapshots = zfs.GetSnapshots(target_path, prefix)

        if target_snapshots:
            # There is already a backup snapshot, so we want to create an
            # incremental snapshot
            last_target_snapshot = sorted(target_snapshots,
                                          key=lambda x: x.Timestamp)[-1]

            print(f"Creating backup of '{fs}@{snapshot_name}' to "
                  f"'{target_path}'")

            call = ['zfs', 'send',
                    '-i', f"{fs}@{last_target_snapshot.Name}",
                    f"{fs}@{snapshot_name}",
                    '|',
                    'zfs', 'recv', '-Fuv', target_path]
        else:
            print(f"Creating backup of '{fs}@{snapshot_name}' to "
                  f"'{target_path}'")

            call = ['zfs', 'send',
                    f"{fs}@{snapshot_name}",
                    '|',
                    'zfs', 'recv', '-Fuv', target_path]

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
