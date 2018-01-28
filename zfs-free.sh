#!/bin/bash
CUR_PATH=`pwd`

USED=$((`sudo zfs get -o value -Hp used $CUR_PATH` / 1024)) > /dev/null
AVAIL=$((`sudo zfs get -o value -Hp available $CUR_PATH` / 1024)) > /dev/null
TOTAL=$(($USED+$AVAIL)) > /dev/null
echo $TOTAL $AVAIL 1024
