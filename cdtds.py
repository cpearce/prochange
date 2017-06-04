from fptree import FPTree
from item import Item
from collections import Counter
from collections import deque
import math


class Bucket:
    def __init__(self, transaction=None):
        self.transactions = []
        self.item_count = Counter()
        if transaction is not None:
            self.add(transaction)

    def add(self, transaction):
        self.transactions += [transaction]
        for item in transaction:
            self.item_count[item] += 1

    def size(self):
        return len(self.transactions)

    def append(self, other_bucket):
        for transaction in other_bucket.transactions:
            self.add(transaction)


class BucketList:
    def __init__(self, max_capacity):
        assert(max_capacity >= 1)
        self.max_capacity = max_capacity
        self.buckets = []

    def add(self, transaction):
        # Insert transaction into bucket list.
        self.buckets += [Bucket(transaction)]

        # Merge bucket list to ensure exponential histogram property maintained.
        # Find each contiguous range of buckets with the same capacity
        # with a size which is the same power of 2.
        start = 0
        while start < len(self.buckets):
            if not float.is_integer(math.log2(self.buckets[start].size())):
                start += 1
                continue
            # Bucket size is an exact power of 2. Find number of contiguous
            # buckets with same size.
            end = start
            while (end + 1 < len(self.buckets) and
                   self.buckets[end + 1].size() == self.buckets[start].size()):
                end += 1

            if end - start < self.max_capacity:
                # We don't have (max_capacity + 1) contiguous buckets. Skip
                # ahead to the end of the range.
                start = end + 1
                continue

            # Merge two oldest buckets.
            self.buckets[start].append(self.buckets[start + 1])
            self.buckets.pop(start + 1)


def change_detection_transaction_data_streams(transactions,
                                              min_support,
                                              max_capacity):
    bucket_list = BucketList(max_capacity)
    num_transactions = 0
    for transaction in [list(map(Item, t)) for t in transactions]:
        num_transactions += 1

        # Insert transaction into bucket list.
        bucket_list.add(transaction)

