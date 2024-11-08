# SPDX-License-Identifier: BSD-2-Clause

import datetime
import subprocess
import syslog
from typing import Optional

__version__ = '1.0'


class ZfsSnapshot:
    '''Represents a single ZFS snapshot.'''
    def __init__(self, path, name, date):
        self._path = path
        self._name = name
        self._date = date

    @property
    def Timestamp(self):
        return self._date

    @property
    def Name(self):
        return self._name

    @property
    def Path(self):
        return self._path

    def __str__(self):
        return 'Snapshot: {}@{} : {}'.format(
            self._path, self._name, self._date)

    def __repr__(self):
        return 'ZfsSnapshot({}, {}, {})'.format(
            repr(self._path),
            repr(self._name),
            repr(self._date))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __key(self):
        return (self._path, self._name, self._date,)


def _SnapshotFromOutput(line):
    # ZFS probably doesn't support snapshot names containing '@' but to be
    # safe we specify max-splits at 1

    snapshot_name, timestamp = line.split()
    snapshot_path, name = snapshot_name.split('@', 1)

    timestamp = datetime.datetime.fromtimestamp(int(timestamp),
                                                tz=datetime.timezone.utc)

    return ZfsSnapshot(snapshot_path, name, timestamp)


def GetSnapshot(path, snapshot_name) -> Optional[ZfsSnapshot]:
    '''Try to get a ZFS snapshot for a given path and snapshot name'''
    try:
        zfs_output = subprocess.check_output(
            ['zfs', 'list', '-Ht', 'snapshot', '-p',
             '-o', 'name,creation', f'{path}@{snapshot_name}']
            ).decode('utf-8').split('\n')
        print(zfs_output)
        # One line output, one trailing newline
        assert len(zfs_output) == 2
        return _SnapshotFromOutput(zfs_output[0].strip())
    except Exception:
        return None


def GetSnapshots(path, prefix='shadow_copy') -> list[ZfsSnapshot]:
    '''Get all snapshots for a path as a list of ZfsSnapshot.

    Snapshots can be filtered by providing a prefix. The timestamp
    is parsed from the file system and provided in UTC.'''
    try:
        zfs_output = subprocess.check_output(
            ['zfs', 'list', '-Ht', 'snapshot', '-p',
             '-o', 'name,creation', path]).decode('utf-8').split('\n')
    except Exception:
        return []

    snapshotNames = [line.strip() for line in zfs_output if line]
    snapshots = []

    for n in snapshotNames:
        snapshot = _SnapshotFromOutput(n)
        assert path == snapshot.Path

        if not snapshot.Name.startswith(prefix):
            continue

        snapshots.append(snapshot)

    return snapshots


def CreateSnapshot(path, name, recursive=True, dryRun=False) -> ZfsSnapshot:
    '''Create a snapshot for the pool or filesystem.'''

    args = ['zfs', 'snapshot']

    if recursive:
        args.append('-r')

    args.append('{}@{}'.format(path, name))

    if dryRun:
        print(' '.join(args))
    else:
        subprocess.check_call(args)
        syslog.syslog(syslog.LOG_INFO,
                      'Created snapshot: {}@{}'.format(path, name))

    return ZfsSnapshot(path, name, datetime.datetime.now(
        tz=datetime.timezone.utc))


def DestroySnapshot(path, name, recursive=True, dryRun=False):
    '''Destroy a snapshot at the provided path with the provided name.'''
    snapshot_name = f'{path}@{name}'

    args = ['zfs', 'destroy']
    if recursive:
        args.append('-r')
    args.append(snapshot_name)

    if dryRun:
        print(' '.join(args))
    else:
        subprocess.check_call(args)
        syslog.syslog(syslog.LOG_INFO,
                      f'Destroyed snapshot: {snapshot_name}')


def GetPools() -> list[str]:
    '''Find all ZFS pools.'''
    zp = subprocess.check_output(['zpool', 'list', '-H', '-o', 'name']).decode(
        'utf-8').split('\n')
    return [line.strip() for line in zp if line]


def GetFilesystems(path=None) -> list[str]:
    '''Find all ZFS filesystems'''
    args = [
        'zfs', 'list', '-H', '-t', 'filesystem', '-o', 'name'
    ]

    if path:
        args.append(path)

    zp = subprocess.check_output(args).decode('utf-8').split('\n')
    return [line.strip() for line in zp if line]

def GetVolumes() -> list[str]:
    '''Find all volumes'''
    args = [
        'zfs', 'list', '-H', '-t', 'volume', '-o', 'name'
    ]

    zp = subprocess.check_output(args).decode('utf-8').split('\n')
    return [line.strip() for line in zp if line]
