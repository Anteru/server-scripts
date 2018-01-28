#!/usr/bin/env python3

# SPDX-License-Identifier: BSD-2-Clause

import libvirt
import syslog
from xml.etree import ElementTree
import os
import time
import shutil
import configparser

def GetFilesToBackup (domainXml):
    """Get the disks file names from the domain XML description."""
    disks = root.findall ('./devices/disk/source')

    files = []
    for disk in disks:
        files.append (disk.get ('file'))

    return files

if __name__ == '__main__':
    config = configparser.ConfigParser ()

    config ['Backup'] = {
        'directory' : '/tank/VM',
        'timeout' : 120
    }

    config.read (['/etc/backup-vm.cfg'])

    backup_directory = config ['Backup']['directory']
    backup_timeout = int (config ['Backup']['timeout'])

    conn = libvirt.open ('qemu:///system')

    if conn is None:
        syslog.syslog (syslog.LOG_ERR, 'Could not open connection to KVM')
        sys.exit (1)
    else:
        syslog.syslog (syslog.LOG_INFO, 'Connected to KVM')

    domains = conn.listAllDomains()
    if domains is None:
        syslog.syslog (syslog.LOG_ERR, 'Could not list domains')

    for dom in domains:
        name = dom.name ()
        xml = dom.XMLDesc (0)
        startVM = False

        root = ElementTree.fromstring (xml)
        files = GetFilesToBackup (root)

        if dom.isActive():
            syslog.syslog (syslog.LOG_INFO, 'Shutting down active VM "{0}"'.format (name))

            dom.shutdown ()

            for i in range(backup_timeout):
                time.sleep (1)
                state, _ = dom.state ()

                if state == libvirt.VIR_DOMAIN_SHUTOFF:
                    break

            state, _ = dom.state ()
            if state != libvirt.VIR_DOMAIN_SHUTOFF:
                syslog.syslog (syslog.LOG_ERR, 'Could not shutdown VM "{0}"'.format (name))
                continue

            syslog.syslog (syslog.LOG_INFO, 'Shut down VM "{0}", backing up'.format (name))
            startVM = True

        for f in files:
            syslog.syslog (syslog.LOG_INFO,
                'Backing up "{0}" to "{1}" for VM "{2}"'.format (f, backup_directory, name))
            shutil.copy (f, backup_directory)

        syslog.syslog (syslog.LOG_INFO,
            'Backing up XML description for VM "{0}"'.format (name))
        open (os.path.join (backup_directory, name + '.xml'), 'w').write (xml)

        if startVM:
            syslog.syslog (syslog.LOG_INFO, 'Starting VM "{0}"'.format (name))
            dom.create ()

