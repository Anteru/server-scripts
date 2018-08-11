#!/usr/bin/env python3

# SPDX-License-Identifier: BSD-2-Clause

from zfs import (
	CreateSnapshot,
	DestroySnapshot,
	FilterSnapshots,
	FindPools,
	GetSnapshots,
)

import syslog

if __name__=='__main__':
	syslog.openlog('zfs-snapshot')

	for pool in FindPools ():
		syslog.syslog (syslog.LOG_INFO,
			'Processing pool "{0}"'.format (pool))
		CreateSnapshot (pool)
		snapshots = GetSnapshots (pool)
		activeSnapshots, obsoleteSnapshots = FilterSnapshots (snapshots)
		for snapshot in obsoleteSnapshots:
			DestroySnapshot (pool, snapshot)
