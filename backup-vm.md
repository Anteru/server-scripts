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
- 1.2:
  - Add `exclude` to exclude VMs from the backup
  - Add `skip_copy_if_same` to skip copying VM images when nothing changed (default: `true`)
- 1.3:
  - Refactor code
  - Put each VM into a directory

Configuration format
--------------------

The configuration uses [TOML](https://toml.io). If not specified, the defaults will be used, which will backup all VMs to `/tank/VM`.

```toml
destination = "/tank/VM"

# Timeout to wait during shutoff in seconds
timeout = 120

# For each VM in this list, the storage files won't be backed up
# This is case-insensitive
skip_storage = ["simple_vm"]

# Exclude all VMs in this list from the backup
exclude = ["test_vm"]

# Skip the copy if the source and destination file image are the same
skip_copy_if_same = true
```
