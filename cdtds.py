from fptree import FPTree
from fptree import sort_transaction
from item import Item
from collections import Counter
from collections import deque
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
        return "BucketList[" + ", ".join(map(str, self.buckets)) + "]"


def find_local_drift(bucket_list, local_cut, min_len):
    # Find the index in bucket list where local drift occurs; where
    # item frequencies change significantly.
    cut = 1
    while cut < len(bucket_list):
        # Create a Counter() for the item frequencies before and after the
        # cut point.
        prev_item_count = sum(
            [bucket.tree.item_count for bucket in bucket_list[0:cut]], Counter())
        curr_item_count = sum(
            [bucket.tree.item_count for bucket in bucket_list[cut:]], Counter())

        prev_len = sum([len(bucket) for bucket in bucket_list[0:cut]])
        curr_len = sum([len(bucket) for bucket in bucket_list[cut:]])

        if prev_len > min_len and curr_len > min_len:
            # Check if any item's frequency has a significant difference.
            for item in curr_item_count.keys():
                prev_support = prev_item_count[item] / prev_len
                curr_support = curr_item_count[item] / curr_len
                if abs(prev_support - curr_support) >= local_cut:
                    return cut
        cut += 1
    return None


def change_detection_transaction_data_streams(transactions,
                                              local_cut,
                                              max_capacity,
                                              min_local_cut_len):
    assert(local_cut > 0 and local_cut <= 1)
    bucket_list = BucketList(max_capacity)
    num_transactions = 0
    for transaction in [list(map(Item, t)) for t in transactions]:
        num_transactions += 1

        # Insert transaction into bucket list. Bucket list will merge
        # buckets as necessary to maintain exponential histogram.
        bucket_list.add(transaction)

        # Check for local drift, as the check is cheap.
        cut_index = find_local_drift(bucket_list, local_cut, min_local_cut_len)
        if cut_index is not None:
            bucket_list[0:cut_index] = []
