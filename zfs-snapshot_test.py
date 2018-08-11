# SPDX-License-Identifier: BSD-2-Clause
from zfs import (
    ZfsSnapshot,
    FilterSnapshots,
    YearlyFilter,
    WeeklyFilter,
    MonthlyFilter
)

import datetime

def test_FilterSnapshotsYearly ():
    snapshots = [
        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 1, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 2, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 3, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 4, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 5, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 6, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 7, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 8, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 9, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 10, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 11, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 12, 1, 12, 0, 0)),
    ]

    keep, delete = FilterSnapshots (snapshots,
        datetime.datetime (2001, 1, 1),
        filters = [(YearlyFilter (), datetime.timedelta (),),
                   (None, datetime.timedelta.max)])

    assert len(keep) == 1
    keep = list(keep)
    assert keep[0].Timestamp == datetime.datetime (2000, 12, 1, 12, 0, 0)

def test_FilterSnapshotsWeeklyMonthly ():
    snapshots = [
        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 1, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 1, 8, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 1, 15, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 1, 22, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 1, 29, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 2, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 2, 8, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 2, 15, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 2, 22, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 3, 1, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 3, 8, 12, 0, 0)),

        ZfsSnapshot ('tank', 'shadow_copy',
            datetime.datetime (2000, 3, 15, 12, 0, 0)),
    ]

    keep, delete = FilterSnapshots (snapshots,
        datetime.datetime (2000, 4, 1),
        filters = [(WeeklyFilter (), datetime.timedelta (),),
                   (MonthlyFilter (), datetime.timedelta (30)),
                   (None, datetime.timedelta.max)])

    # 3 for March, 1 for February, 1 for January
    assert len(keep) == 5
    assert snapshots[-1] in keep
    assert snapshots[-2] in keep
    assert snapshots[-3] in keep
    assert snapshots[-4] in keep
    assert snapshots[4] in keep

    # We expect the list to be sorted newest to oldest
    assert (delete [0].Timestamp == datetime.datetime (2000, 2, 15, 12, 0, 0))
    assert (delete [-1].Timestamp == datetime.datetime (2000, 1, 1, 12, 0, 0))
