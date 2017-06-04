from cdtds import BucketList
from item import Item
from cdtds import change_detection_transaction_data_streams
from fptree import count_item_frequency_in

def test_BucketList_bucket_sizes():
    test_cases = [(1, [[1], [2], [2, 1], [2, 2]]),
                 (2, [[1], [1, 1], [2,1], [2, 1, 1], [2, 2, 1]])]
    for (capacity, expected_lengths) in test_cases:
        bucket_list = BucketList(capacity)
        for lengths in expected_lengths:
            bucket_list.add([Item("a")])
            assert([x.size() for x in bucket_list.buckets] == lengths)

def test_BucketList_item_counts():
    transactions = [
        ["a", "b"],
        ["b", "c", "d"],
        ["a", "c", "d", "e"],
        ["a", "d", "e"],
        ["a", "b", "c"],
        ["a", "b", "c", "d"],
        ["a"],
        ["a", "b", "c"],
        ["a", "b", "d"],
        ["b", "c", "e"],
    ]
    item_count = count_item_frequency_in(transactions)
    bucket_list = BucketList(1)
    # Note: map() produces a generator which can be evaluated only once,
    # so we need to force it to evaluate, otherwise it can't be stored in
    # the bucket list safely.
    for transaction in [list(map(Item, t)) for t in transactions]:
        bucket_list.add(transaction)
    for item in item_count.keys():
        count = 0
        for bucket in bucket_list.buckets:
            count += bucket.item_count[item]
        assert(count == item_count[item])
        count = sum([bucket.item_count[item] for bucket in bucket_list.buckets])
        assert(count == item_count[item])

# def test_cdtds():
#     transactions = [
#         ["a", "b"],
#         ["b", "c", "d"],
#         ["a", "c", "d", "e"],
#         ["a", "d", "e"],
#         ["a", "b", "c"],
#         ["a", "b", "c", "d"],
#         ["a"],
#         ["a", "b", "c"],
#         ["a", "b", "d"],
#         ["b", "c", "e"],
#     ]

#     change_detection_transaction_data_streams(transactions, 0.3, 1)
