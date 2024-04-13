#!/usr/bin/env python3

# SPDX-License-Identifier: BSD-2-Clause

import libvirt
import syslog
import sys
from xml.etree import ElementTree
import os
import time
import shutil
import argparse
import hashlib
import pathlib

try:
    import tomllib as toml
except ImportError:
    import tomli as toml

__version__ = '1.2'


def GetFilesToBackup(domainXml):
    """Get the disks file names from the domain XML description."""
    disks = root.findall("./devices/disk/source")

    files = []
    for disk in disks:
        files.append(disk.get("file"))

    return files

def compute_checksums(path):
    hasher = hashlib.sha1(usedforsecurity=False)

    with open(path, 'rb') as input_file:
        while buffer := input_file.read(64 << 20):
            hasher.update(buffer)
    return hasher.digest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=argparse.FileType('rb'))

    args = parser.parse_args()

    config = {
        'destination': '/tank/VM',
        'timeout': 120,
        'skip_storage': [],
        # This will calculate checksum files and skip copies if files
        # turn out to be the same
        'skip_copy_if_same': True,
        # Exclude the following VMs
        'exclude' : []
    }

    if args.config:
        config.update (toml.load(args.config))

    backup_directory = config['destination']
    backup_timeout = config['timeout']
    skip_storage = set(map(str.lower, config['skip_storage']))
    ignore_list = set(map(str.lower, config['exclude']))

    conn = libvirt.open("qemu:///system")

    if conn is None:
        syslog.syslog(syslog.LOG_ERR, "Could not open connection to KVM")
        sys.exit(1)
    else:
        syslog.syslog(syslog.LOG_INFO, "Connected to KVM")

    domains = conn.listAllDomains()
    if domains is None:
        syslog.syslog(syslog.LOG_ERR, "Could not list domains")

    for dom in domains:
        name: str = dom.name()

        if name.lower() in ignore_list:
            syslog.syslog(syslog.LOG_INFO, f'Ignoring VM "{name}"')
            continue

        xml = dom.XMLDesc(0)
        startVM = False

        root = ElementTree.fromstring(xml)

        # If we skip storage, there's no point in shutting down the VM
        if dom.isActive() and name.lower() not in skip_storage:
            syslog.syslog(
                syslog.LOG_INFO, 'Shutting down active VM "{0}"'.format(name)
            )

            dom.shutdown()

            for i in range(backup_timeout):
                time.sleep(1)
                state, _ = dom.state()

                if state == libvirt.VIR_DOMAIN_SHUTOFF:
                    break

            state, _ = dom.state()
            if state != libvirt.VIR_DOMAIN_SHUTOFF:
                syslog.syslog(
                    syslog.LOG_ERR, 'Could not shutdown VM "{0}"'.format(name)
                )
                continue

            syslog.syslog(
                syslog.LOG_INFO, 'Shut down VM "{0}", backing up'.format(name)
            )
            startVM = True

        if name.lower() not in skip_storage:
            files = GetFilesToBackup(root)
            for f in files:
                syslog.syslog(
                    syslog.LOG_INFO,
                    'Backing up "{0}" to "{1}" for VM "{2}"'.format(
                        f, backup_directory, name
                    ),
                )

                if config['skip_copy_if_same']:
                    destination_file = pathlib.Path(backup_directory) / \
                        pathlib.Path(f).name
                    hash_file = destination_file.with_suffix('.hash')

                    destination_hash = None
                    if hash_file.exists():
                        destination_hash = hash_file.read_bytes()

                    source_hash = compute_checksums(f)

                    if destination_hash != source_hash:
                        syslog.syslog(syslog.LOG_INFO,
                            'Files changed, executing copy')
                        shutil.copy(f, backup_directory)
                        hash_file.write_bytes(source_hash)
                    else:
                        syslog.syslog(syslog.LOG_INFO,
                            'No file changes, skipping copy')
                else:
                    shutil.copy(f, backup_directory)
        else:
            syslog.syslog(syslog.LOG_INFO,
                          f'Skipping storage for VM "{name}"')

        syslog.syslog(
            syslog.LOG_INFO,
            'Backing up XML description for VM "{0}"'.format(name),
        )
        open(os.path.join(backup_directory, name + ".xml"), "w").write(xml)

        if startVM:
            syslog.syslog(syslog.LOG_INFO, 'Starting VM "{0}"'.format(name))
            dom.create()