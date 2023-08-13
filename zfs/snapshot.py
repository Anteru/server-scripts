import operator
import datetime
from configparser import ConfigParser


class Filter:
    """Filters a list of snapshots."""

    def Apply(self, snapshots):
        return snapshots


class PassthroughFilter(Filter):
    pass


class BucketFilter(Filter):
    """Filter snapshots into a bucket. The bucket groups snapshots together,
    and the filter returns the newest item in each bucket.

    The ``GetBucket`` function determines which bucket a snapshot belongs to.
    """

    def GetBucket(self, timestamp):
        return timestamp

    def Apply(self, snapshots):
        buckets = {}

        for snapshot in snapshots:
            bucket = self.GetBucket(snapshot.Timestamp)
            if bucket not in buckets:
                buckets[bucket] = []
            buckets[bucket].append(snapshot)
        return self.GetNewestPerBucket(buckets)

    def GetNewestPerBucket(self, buckets):
        """Buckets must be a dictionary [bucket] -> list of snapshots.

        This will return the newest snapshot in each bucket."""
        result = []

        for bucket in buckets.values():
            result.append(
                sorted(bucket, key=operator.attrgetter("Timestamp"))[-1]
            )

        return result


class HourlyFilter(BucketFilter):
    def GetBucket(self, timestamp):
        return datetime.datetime(
            year=timestamp.year,
            month=timestamp.month,
            day=timestamp.day,
            hour=timestamp.hour,
            tzinfo=timestamp.tzinfo,
        )


class DailyFilter(BucketFilter):
    def GetBucket(self, timestamp):
        return datetime.datetime(
            year=timestamp.year,
            month=timestamp.month,
            day=timestamp.day,
            tzinfo=timestamp.tzinfo,
        )


class WeeklyFilter(BucketFilter):
    def GetBucket(self, timestamp):
        iso = timestamp.isocalendar()
        return (
            iso[0],
            iso[1],
        )


class MonthlyFilter(BucketFilter):
    def GetBucket(self, timestamp):
        return datetime.datetime(
            year=timestamp.year,
            month=timestamp.month,
            day=1,
            tzinfo=timestamp.tzinfo,
        )


class YearlyFilter(BucketFilter):
    def GetBucket(self, timestamp):
        return datetime.datetime(
            year=timestamp.year, month=1, day=1, tzinfo=timestamp.tzinfo
        )


__DEFAULT_FILTERS = [
    # Filter name; maximum age until this filter should get applied
    (PassthroughFilter(), datetime.timedelta(days=2)),
    (HourlyFilter(), datetime.timedelta(days=7)),
    (DailyFilter(), datetime.timedelta(days=30)),
    (WeeklyFilter(), datetime.timedelta(days=90)),
    (MonthlyFilter(), datetime.timedelta(days=365)),
    (YearlyFilter(), datetime.timedelta.max),
]


def __BuildFilters(s):
    filters = [
        (
            "all",
            PassthroughFilter,
        ),
        (
            "hourly",
            HourlyFilter,
        ),
        (
            "daily",
            DailyFilter,
        ),
        (
            "weekly",
            WeeklyFilter,
        ),
        (
            "monthly",
            MonthlyFilter,
        ),
        (
            "yearly",
            YearlyFilter,
        ),
    ]

    result = []
    for filterName, filterClass in filters:
        if filterName in s:
            cutoff = s[filterName]

            if cutoff == "0" or cutoff == "disabled":
                continue

            if cutoff == "unlimited":
                cutoff = datetime.timedelta.max
            else:
                cutoff = datetime.timedelta(int(cutoff))
            result.append(
                (
                    filterClass(),
                    cutoff,
                )
            )

    return result


def ParseConfiguration(configFile):
    config = ConfigParser()
    config.read_file(configFile)

    result = {}
    for section in config.sections():
        result[section] = {"filters": __BuildFilters(config[section])}

        # Must match the default config below
        result[section]["recursive"] = config.getboolean(
            section, "recursive", fallback=True
        )
        result[section]["ignore"] = config.getboolean(
            section, "ignore", fallback=False
        )

    if "_default" not in config:
        result.update(GetDefaultConfiguration())

    return result


def GetDefaultConfiguration():
    return {
        "_default": {
            "filters": __DEFAULT_FILTERS,
            "recursive": True,
            "ignore": False,
        }
    }


def FilterSnapshots(snapshots, currentTime=None, filters=__DEFAULT_FILTERS):
    """Filter snapshots and return a tuple of snapshots to keep and to
       delete."""

    if currentTime is None:
        currentTime = datetime.datetime.now(datetime.timezone.utc)

    def Partition(snapshots, condition):
        """Partition a list into a two lists based on a condition.

        Returns a tuple, the first items contains a list of all elements for
        which the condition was true, the second all for which it was false."""
        trueList = []
        falseList = []
        for element in snapshots:
            if condition(element):
                trueList.append(element)
            else:
                falseList.append(element)
        return (trueList, falseList)

    toKeep = set()
    remainingSnapshots = snapshots

    for currentFilter, cutoff in filters:
        if not remainingSnapshots:
            break
        # Partition such that currentSnapshots are all < cutoff
        currentSnapshots, remainingSnapshots = Partition(
            remainingSnapshots,
            # The assumption is that currentTime is always >= snapshot.Timestamp
            lambda snapshot: (currentTime - snapshot.Timestamp) <= cutoff,
        )
        toKeep.update(currentFilter.Apply(currentSnapshots))

    # If some entries remain, we want to keep them, as they're even older
    # and there was no policy set for very old snapshots
    toKeep.update(remainingSnapshots)

    toDelete = set(snapshots)
    toDelete.difference_update(toKeep)

    # Deleting in reversed order is supposed to be better
    # http://serverfault.com/questions/340837/how-to-delete-all-but-last-n-zfs-snapshots
    # Doesn't cost us much to do it here, so why not
    return (
        toKeep,
        sorted(toDelete, key=operator.attrgetter("Timestamp"), reverse=True),
    )