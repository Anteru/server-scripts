# SPDX-License-Identifier: BSD-2-Clause
from . import (
    ZfsSnapshot,
)

from .snapshot import (
    FilterSnapshots,
    HourlyFilter,
    DailyFilter,
    YearlyFilter,
    WeeklyFilter,
    MonthlyFilter,
    ParseConfiguration,
    PassthroughFilter,
)

import datetime


def test_FilterSnapshotsYearly():
    snapshots = [
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 1, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 2, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 3, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 4, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 5, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 6, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 7, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 8, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 9, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 10, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 11, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 12, 1, 12, 0, 0)
        ),
    ]

    keep, _ = FilterSnapshots(
        snapshots,
        datetime.datetime(2001, 1, 1),
        filters=[
            (
                YearlyFilter(),
                datetime.timedelta.max,
            )
        ],
    )

    assert len(keep) == 1
    keep = list(keep)
    assert keep[0].Timestamp == datetime.datetime(2000, 12, 1, 12, 0, 0)


def test_FilterSnapshotsDefaultForOlderIsKeep():
    snapshots = [
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(1998, 1, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(1999, 1, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 1, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 12, 1, 12, 0, 0)
        ),
    ]

    keep, _ = FilterSnapshots(
        snapshots,
        currentTime=datetime.datetime(2001, 1, 1),
        filters=[
            (
                YearlyFilter(),
                datetime.timedelta(days=367),
            )
        ],
    )

    assert len(keep) == 3


def test_FilterSnapshotsWeeklyMonthly():
    snapshots = [
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 1, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 1, 8, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 1, 15, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 1, 22, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 1, 29, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 2, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 2, 8, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 2, 15, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 2, 22, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 3, 1, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 3, 8, 12, 0, 0)
        ),
        ZfsSnapshot(
            "tank", "shadow_copy", datetime.datetime(2000, 3, 15, 12, 0, 0)
        ),
    ]

    keep, delete = FilterSnapshots(
        snapshots,
        currentTime=datetime.datetime(2000, 4, 1),
        filters=[
            (
                WeeklyFilter(),
                datetime.timedelta(30),
            ),
            (
                MonthlyFilter(),
                datetime.timedelta.max,
            ),
        ],
    )

    # 3 for March, 1 for February, 1 for January
    assert len(keep) == 5
    assert snapshots[-1] in keep
    assert snapshots[-2] in keep
    assert snapshots[-3] in keep
    assert snapshots[-4] in keep
    assert snapshots[4] in keep

    # We expect the list to be sorted newest to oldest
    assert delete[0].Timestamp == datetime.datetime(2000, 2, 15, 12, 0, 0)
    assert delete[-1].Timestamp == datetime.datetime(2000, 1, 1, 12, 0, 0)


def test_ParseConfiguration():
    from io import BytesIO

    configString = BytesIO(
        """
[_default]

all = 2
hourly = 7
daily = 30
weekly = 90
monthly = 365
yearly = "unlimited"

["tank/VM"]

all = 0
hourly = 0
daily = 30
weekly = 90
monthly = 365
yearly = "unlimited"
    """.encode('utf-8')
    )

    configuration = ParseConfiguration(configString)
    assert "_default" in configuration
    assert "tank/VM" in configuration

    assert isinstance(
        configuration["_default"]["filters"][0][0], PassthroughFilter
    )
    assert isinstance(configuration["_default"]["filters"][1][0], HourlyFilter)
    assert isinstance(configuration["_default"]["filters"][2][0], DailyFilter)
    assert isinstance(configuration["_default"]["filters"][3][0], WeeklyFilter)
    assert isinstance(
        configuration["_default"]["filters"][4][0], MonthlyFilter
    )
    assert isinstance(configuration["_default"]["filters"][5][0], YearlyFilter)

    assert configuration["_default"]["filters"][0][1] == datetime.timedelta(2)
    assert configuration["_default"]["filters"][1][1] == datetime.timedelta(7)
    assert configuration["_default"]["filters"][2][1] == datetime.timedelta(30)
    assert configuration["_default"]["filters"][3][1] == datetime.timedelta(90)
    assert configuration["_default"]["filters"][4][1] == datetime.timedelta(
        365
    )
    assert configuration["_default"]["filters"][5][1] == datetime.timedelta.max

    assert isinstance(configuration["tank/VM"]["filters"][0][0], DailyFilter)
    assert isinstance(configuration["tank/VM"]["filters"][1][0], WeeklyFilter)
    assert isinstance(configuration["tank/VM"]["filters"][2][0], MonthlyFilter)
    assert isinstance(configuration["tank/VM"]["filters"][3][0], YearlyFilter)

    assert configuration["tank/VM"]["filters"][0][1] == datetime.timedelta(30)
    assert configuration["tank/VM"]["filters"][1][1] == datetime.timedelta(90)
    assert configuration["tank/VM"]["filters"][2][1] == datetime.timedelta(365)
    assert configuration["tank/VM"]["filters"][3][1] == datetime.timedelta.max


def test_ConfigOrderHasNoImpactOnSort():
    from io import BytesIO

    configString = BytesIO(
        """
[tank]

hourly = 2
daily = 5

[dozer]

daily = 5
hourly = 2
""".encode('utf-8')
    )

    configuration = ParseConfiguration(configString)

    snapshots = []
    for i in range(24):
        snapshots.append(ZfsSnapshot('tank', str(i),
                                     datetime.datetime(2000, 1, 1)
                                     + datetime.timedelta(hours=i * 8)))
        snapshots.append(ZfsSnapshot('dozer', str(i),
                                     datetime.datetime(2000, 1, 1)
                                     + datetime.timedelta(hours=i * 8)))

    tank_filtered = FilterSnapshots(snapshots, datetime.datetime(2000, 1, 8),
                                    configuration['tank']['filters'])
    dozer_filtered = FilterSnapshots(snapshots, datetime.datetime(2000, 1, 8),
                                     configuration['dozer']['filters'])

    assert tank_filtered == dozer_filtered
