#!/usr/bin/env python3

# SPDX-License-Identifier: BSD-2-Clause

import datetime
import subprocess
import operator
import time
import syslog

class ZfsSnapshot:
	'''Represents a single ZFS snapshot.'''
	def __init__ (self, path, name, date):
		self._path = path
		self._name = name
		self._date = date

	def GetTimestamp (self):
		return self._date

	def GetName (self):
		return self._name

	def GetPath (self):
		return self._path

	def __str__ (self):
		return 'Snapshot: {}@{} : {}'.format (self._path, self._name, self._date)

	def __repr__ (self):
		return 'ZfsSnapshot ({}, {}, {})'.format (repr (self._path),
			repr (self._name),
			repr (self._date))

	def __hash__ (self):
		return hash(self.__key ())

	def __eq__ (self, other):
		return self.__key () == other.__key ()

	def __key (self):
		return (self._path, self._name, self._date)

def GetSnapshots (pool):
	'''Get all snapshots for a pool as a list of ZfsSnapshot.

	All means all snapshots created using this tool, that is, snapshots starting
	with shadow_copy -- for those, we know the time zone.'''
	s = subprocess.check_output (['zfs', 'list', '-Ht', 'snapshot']).decode ('utf-8').split ('\n')
	# This will also get rid of empty lines
	s = [l.split ('\t') for l in s if l]

	snapshotNames = [l [0] for l in s]
	snapshots = []

	for n in snapshotNames:
		path = n [:n.find ('@')]

		if path != pool:
			continue

		nameDate = n [n.find ('@')+1:]
		name = None
		timestamp = None
		if nameDate.startswith ('shadow_copy'):
			name = 'shadow_copy'
			# Our snapshots are in UTC time
			timestampUtcTime = time.strptime (nameDate [nameDate.find ('-')+1:],
				'%Y.%m.%d-%H.%M.%S')
			timestamp = datetime.datetime (*(timestampUtcTime [0:6]),
				tzinfo=datetime.timezone.utc)
		else:
			# unknown format, can't parse date, so ignore and continue
			continue

		snapshots.append (ZfsSnapshot (path, name, timestamp))

	return snapshots

def CreateSnapshot (pool):
	'''Create a shadow copy snapshot for the pool.'''
	dt = datetime.datetime.utcnow ()
	snapshotName = dt.strftime ('shadow_copy-%Y.%m.%d-%H.%M.%S')
	subprocess.check_call (['zfs', 'snapshot', '-r', '{}@{}'.format (pool, snapshotName)])
	syslog.syslog (syslog.LOG_INFO, 'Created snapshot: {0}'.format (snapshotName))
	return ZfsSnapshot (pool, 'shadow_copy', dt)

def DestroySnapshot (pool, snapshot):
	'''Destroy a shadow copy snapshot in the provided pool.'''
	# Safety checks
	if snapshot.GetName () != 'shadow_copy':
		return

	if snapshot.GetPath () != pool:
		return

	snapshotName = snapshot.GetTimestamp ().strftime ('shadow_copy-%Y.%m.%d-%H.%M.%S')
	subprocess.check_call (['zfs', 'destroy', '-r', '{}@{}'.format (pool, snapshotName)])
	syslog.syslog (syslog.LOG_INFO, 'Destroyed snapshot: {0}'.format (snapshotName))

def FindPools ():
	'''Find all ZFS pools.'''
	zp = subprocess.check_output (['zpool', 'list', '-H']).decode ('utf-8').split ('\n')
	return [l.split () [0] for l in zp if l]

class Filter:
	'''Filters a list of snapshots.'''
	def Apply (self, snapshots):
		return snapshots

class PassthroughFilter(Filter):
	pass

def GetLastPerBucket (buckets):
	'''Buckets must be a dictionary [bucket] -> list of snapshots.

	This will return the last item in each bucket.'''
	result = []

	for bucket in buckets.values ():
		result.append (sorted (bucket, key=operator.methodcaller ('GetTimestamp')) [-1])

	return result

class HourlyFilter (Filter):
	def Apply (self, snapshots):
		# We group the snapshots by hour
		buckets = {}

		for snapshot in snapshots:
			timestamp = snapshot.GetTimestamp ()
			bucket = datetime.datetime (year=timestamp.year,
				month=timestamp.month, day=timestamp.day, hour=timestamp.hour,
				tzinfo=timestamp.tzinfo)
			if bucket not in buckets:
				buckets [bucket] = []
			buckets [bucket].append (snapshot)
		return GetLastPerBucket (buckets)

class DailyFilter (Filter):
	def Apply (self, snapshots):
		# We group the snapshots by day
		buckets = {}

		for snapshot in snapshots:
			timestamp = snapshot.GetTimestamp ()
			bucket = datetime.datetime (year=timestamp.year,
				month=timestamp.month, day=timestamp.day,
				tzinfo=timestamp.tzinfo)
			if bucket not in buckets:
				buckets [bucket] = []
			buckets [bucket].append (snapshot)
		return GetLastPerBucket (buckets)

class WeeklyFilter (Filter):
	def Apply (self, snapshots):
		# We group the snapshots by calendar week
		buckets = {}

		for snapshot in snapshots:
			timestamp = snapshot.GetTimestamp ()
			iso = timestamp.isocalendar ()
			bucket = (iso [0], iso [1])
			if bucket not in buckets:
				buckets [bucket] = []
			buckets [bucket].append (snapshot)
		return GetLastPerBucket (buckets)

class MonthlyFilter (Filter):
	def Apply (self, snapshots):
		# We group the snapshots by month
		buckets = {}

		for snapshot in snapshots:
			timestamp = snapshot.GetTimestamp ()
			bucket = datetime.datetime (year=timestamp.year,
				month=timestamp.month, day=1, tzinfo=timestamp.tzinfo)
			if bucket not in buckets:
				buckets [bucket] = []
			buckets [bucket].append (snapshot)
		return GetLastPerBucket (buckets)

def FilterSnapshots (s):
	'''Filter snapshots and return a tuple of snapshots to keep and to delete.'''
	def Partition (l, condition):
		'''Partition a list into a two lists based on a condition.

		Returns a tuple, the first items contains a list of all elements for
		which the condition was true, the second all for which it was false.'''
		trueList = []
		falseList = []
		for element in l:
			if condition (element):
				trueList.append (element)
			else:
				falseList.append (element)
		return (trueList, falseList)

	now = datetime.datetime.now (datetime.timezone.utc)
	filterCutoff = [
		# Filter name; minimum snapshot age for this filter to be active
		#			   filter will be applied on all snapshots which are at
		#			   least this old.
		(PassthroughFilter (), datetime.timedelta ()),
		(HourlyFilter (), datetime.timedelta (days=2)),
		(DailyFilter (), datetime.timedelta (days=7)),
		(WeeklyFilter (), datetime.timedelta (days=30)),
		(MonthlyFilter (), datetime.timedelta (days=90)),
		# Dummy entry, the monthly filter should only filter until this cutoff
		(None, datetime.timedelta (days=365))
	]

	toKeep = set ()
	remainingSnapshots = s
	for i in range (len (filterCutoff) - 1):
		currentFilter = filterCutoff [i][0]
		# Partition the input into (cutoff0 ... cutoff1], (cutoff1 ... cutoffN]
		# blocks
		cutoff = filterCutoff [i][1]
		nextCutoff = filterCutoff [i + 1][1]
		activeSnaps, remainingSnaps = Partition (remainingSnapshots,
			lambda s: cutoff < (now - s.GetTimestamp ()) <= nextCutoff)
		toKeep.update (currentFilter.Apply (activeSnaps))

	toDelete = set (s)
	toDelete.difference_update (toKeep)

	# Deleting in reversed order is supposed to be better
	# http://serverfault.com/questions/340837/how-to-delete-all-but-last-n-zfs-snapshots
	# Doesn't cost us much to do it here, so why not
	return (toKeep,
		sorted (toDelete, key=operator.methodcaller ('GetTimestamp'), reverse=True))

if __name__=='__main__':
	syslog.openlog('zfs-snapshot')
	pools = FindPools ()

	for pool in pools:
		syslog.syslog (syslog.LOG_INFO, 'Processing pool "{0}"'.format (pool))
		CreateSnapshot (pool)
		snapshots = GetSnapshots (pool)
		activeSnapshots, obsoleteSnapshots = FilterSnapshots (snapshots)
		for snapshot in obsoleteSnapshots:
			DestroySnapshot (pool, snapshot)
