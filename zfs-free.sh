#!/bin/bash
ZFS=/sbin/zfs   # or /usr/local/sbin/zfs on FreeBSD/TrueNAS

CUR_PATH=$(realpath "$1")
DATASET=$($ZFS list -H -o name "$CUR_PATH" 2>/dev/null)
POOL=${DATASET%%/*}

USED=$(( $($ZFS get -Hp -o value used      "$POOL") / 1024 ))
AVAIL=$(( $($ZFS get -Hp -o value available "$POOL") / 1024 ))
TOTAL=$(( USED + AVAIL ))

echo "$TOTAL $AVAIL 1024"