from fptree import FPTree
from fptree import sort_transaction
from item import Item
import math


class Bucket:
    def __init__(self, transaction=None):
        self.tree = FPTree()
        self.sorting_counter = None
        if transaction is not None:
            self.add(transaction)

    def add(self, transaction):
        self.tree.insert(sort_transaction(transaction, self.sorting_counter))

    def __len__(self):
        return self.tree.num_transactions

    def append(self, other_bucket):
        for (transaction, count) in other_bucket.tree:
            self.tree.insert(
                sort_transaction(
                    transaction,
                    self.sorting_counter),
                count)
        self.tree.sort()  # TODO: Is this necessary?
        self.sorting_counter = self.tree.item_count.copy()

    def __str__(self):
        return str(self.transactions)


class AdaptiveWindow:
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
            if not float.is_integer(math.log2(len(self.buckets[start]))):
                start += 1
                continue
            # Bucket size is an exact power of 2. Find number of contiguous
            # buckets with same size.
            end = start
            while (end + 1 < len(self.buckets) and
                   len(self.buckets[end + 1]) == len(self.buckets[start])):
                end += 1

            if end - start < self.max_capacity:
                # We don't have (max_capacity + 1) contiguous buckets. Skip
                # ahead to the end of the range.
                start = end + 1
                continue

            # Merge two oldest buckets.
            self.buckets[start].append(self.buckets[start + 1])
            self.buckets.pop(start + 1)

    def __len__(self):
        return len(self.buckets)

    def __getitem__(self, index):
        return self.buckets[index]

    def __setitem__(self, index, value):
        self.buckets[index] = value

    def __str__(self):
        return "AdaptiveWindow[" + ", ".join(map(str, self.buckets)) + "]"
