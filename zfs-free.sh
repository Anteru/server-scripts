#!/bin/bash
CUR_PATH=`pwd`

USED=$((`zfs get -o value -Hp used $CUR_PATH` / 1024)) > /dev/null
AVAIL=$((`zfs get -o value -Hp available $CUR_PATH` / 1024)) > /dev/null
TOTAL=$(($USED+$AVAIL)) > /dev/null
echo $TOTAL $AVAIL 1024
