#!/usr/bin/env python3

# SPDX-License-Identifier: BSD-2-Clause
import subprocess
import argparse

try:
    import tomllib as toml
except ImportError:
    import tomli as toml

import zfs

__version__ = '1.1'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=argparse.FileType('rb'))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('TARGET_POOL')

    args = parser.parse_args()

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
