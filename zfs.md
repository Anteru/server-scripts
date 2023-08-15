ZFS utilities
=============

`zfsu` is a script containing several ZFS utilities. Currently, there are two utilities:

* `backup`: Can be used to automate backups of ZFS pools (for example, to an external drive)
* `snapshot`: Automated snapshots with cleanup of old snapshots

Requirements
------------

* Python 3.11 _or_ Python 3.10 with `tomli` installed. On Ubuntu, this can be done system-wide using `apt get install python3-tomli`
* `zfs` must be available

Usage
-----

Both commands support a `--dry-run` argument to check what they would do. Configuration files are written as [TOML](https://toml.io) files.