backup-vm
=========

This script backups VMs managed using `libvirt` (i.e. KVM.) It turns them off, makes a copy of the storage and the XML definition, and turns them back on.

Requirements
------------

* Python 3.11 _or_ Python 3.10 with `tomli` installed. On Ubuntu, this can be done system-wide using `apt get install python3-tomli`
* The `libvirt` Python bindings must be installed. On Ubuntu, use `apt get install python3-libvirt`.

Changelog
---------

- 1.0: Initial release
- 1.1:
  - Change configuration format to TOML
  - Allow ignoring storage of certain VMs (in which case only the XML definition is saved.)

Configuration format
--------------------

The configuration uses [TOML](https://toml.io). If not specified, the defaults will be used, which will backup all VMs to `/tank/VM`.

```toml
destination = /tank/VM

# Timeout to wait during shutoff in seconds
timeout = 120

# For each VM in this list, the storage files won't be backed up
# This is case-insensitive
skip_storage = []
```