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

__version__ = '1.3'


def _get_files_for_vm(domainXml) -> list[pathlib.Path]:
    """Get the disks file names from the domain XML description."""
    disks = root.findall("./devices/disk/source")

    files = []
    for disk in disks:
        if filename := disk.get('file'):
            files.append(pathlib.Path(filename))

    return files


def _compute_checksum(path: pathlib.Path) -> bytes:
    """Compute the SHA1 hashsum for the given file"""
    hasher = hashlib.sha1(usedforsecurity=False)

    with open(path, 'rb') as input_file:
        while buffer := input_file.read(64 << 20):
            hasher.update(buffer)
    return hasher.digest()


def _backup_file(vm_name: str,
                 source_file: pathlib.Path,
                 destination_dir: pathlib.Path,
                 *, skip_copy_if_same=True):
    """Backup a the source file into the destination directory.
    If `skip_copy_if_same` is True, it will calculate the hash of the
    source and destination file first before copying. It will cache the
    destination file's hash in a `.hash` file for future use."""
    syslog.syslog(
        syslog.LOG_INFO,
        'Backing up "{0}" to "{1}" for VM "{2}"'.format(
            source_file, destination_dir, vm_name
        ),
    )

    if skip_copy_if_same:
        destination_file = destination_dir / source_file.name
        hash_file = destination_file.with_suffix('.hash')

        destination_hash = None
        if hash_file.exists():
            destination_hash = hash_file.read_bytes()

        source_hash = _compute_checksum(f)

        if destination_hash != source_hash:
            syslog.syslog(syslog.LOG_INFO, 'Files changed, executing copy')
            shutil.copy(source_file, destination_dir)
            hash_file.write_bytes(source_hash)
        else:
            syslog.syslog(syslog.LOG_INFO, 'No file changes, skipping copy')
    else:
        shutil.copy(source_file, destination_dir)


def _shutdown_vm(name: str, timeout: int, domain: libvirt.virDomain) -> bool:
    """Shutdown a VM within the given timeout. Returns `True`
    if the VM did shut down, otherwise, `False`."""
    syslog.syslog(
        syslog.LOG_INFO, 'Shutting down active VM "{0}"'.format(name)
    )

    domain.shutdown()

    for _ in range(timeout):
        time.sleep(1)
        state, _ = domain.state()

        if state == libvirt.VIR_DOMAIN_SHUTOFF:
            break

    state, _ = domain.state()
    if state != libvirt.VIR_DOMAIN_SHUTOFF:
        syslog.syslog(
            syslog.LOG_ERR, 'Could not shutdown VM "{0}"'.format(name)
        )
        return False

    syslog.syslog(
        syslog.LOG_INFO, 'Shut down VM "{0}", backing up'.format(name)
    )
    return True


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
        'exclude': []
    }

    if args.config:
        config.update(toml.load(args.config))

    backup_root = pathlib.Path(config['destination'])
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

        backup_directory = backup_root / name.lower()
        backup_directory.mkdir(exist_ok=True)

        xml = dom.XMLDesc(0)
        restart_vm = False

        root = ElementTree.fromstring(xml)

        # If we skip storage, there's no point in shutting down the VM
        if dom.isActive() and name.lower() not in skip_storage:
            restart_vm = _shutdown_vm(name, backup_timeout, dom)

        if name.lower() not in skip_storage:
            files = _get_files_for_vm(root)
            for f in files:
                _backup_file(name, f, backup_directory,
                             skip_copy_if_same=config['skip_copy_if_same'])
        else:
            syslog.syslog(syslog.LOG_INFO,
                          f'Skipping storage for VM "{name}"')

        syslog.syslog(
            syslog.LOG_INFO,
            'Backing up XML description for VM "{0}"'.format(name),
        )
        open(os.path.join(backup_directory, name + ".xml"), "w").write(xml)

        if restart_vm:
            syslog.syslog(syslog.LOG_INFO, 'Starting VM "{0}"'.format(name))
            dom.create()
