#!/usr/bin/env python3

# SPDX-License-Identifier: BSD-2-Clause

from zfs import (
	CreateSnapshot,
	DestroySnapshot,
	FilterSnapshots,
	GetFilesystems,
	GetPools,
	GetSnapshots,
	ParseFilters,
	GetDefaultFilters,
)

import syslog
import argparse

if __name__=='__main__':
	parser = argparse.ArgumentParser ()
	parser.add_argument ('-c', '--config', type=argparse.FileType ('r'))
	parser.add_argument ('--dry-run', action='store_true')

	args = parser.parse_args ()

	if args.config is not None:
		config = ParseFilters (args.config)
	else:
		config = GetDefaultFilters ()

	syslog.openlog('zfs-snapshot')

	for pool in GetPools ():
		syslog.syslog (syslog.LOG_INFO,
			'Processing pool "{0}"'.format (pool))
		CreateSnapshot (pool, dryRun = args.dry_run)

	for filesystem in GetFilesystems ():
		snapshots = GetSnapshots (filesystem)

		if filesystem in config:
			activeSnapshots, obsoleteSnapshots = FilterSnapshots (snapshots,
				filters=config [filesystem])
		else:
			activeSnapshots, obsoleteSnapshots = FilterSnapshots (snapshots,
				filters=config ['_default'])

		for snapshot in obsoleteSnapshots:
			DestroySnapshot (filesystem, snapshot, recursive = False, dryRun = args.dry_run)
