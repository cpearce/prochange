from adaptivewindow import AdaptiveWindow
from item import Item
from fptree import count_item_frequency_in

test_transactions = list(map(lambda t: list(map(Item, t)), [
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
]))


def test_AdaptiveWindow_bucket_sizes():
    test_cases = [
        (1, [
            [1], [2], [
                2, 1], [
                2, 2]]), (2, [[], [2], [2], [
                    2, 2], [
                        2, 2], [
                            4, 2], [
                                4, 2], [
                                    4, 2, 2]])]
    for (capacity, expected_lengths) in test_cases:
        window = AdaptiveWindow(capacity, capacity)
        for lengths in expected_lengths:
            window.add([Item("a")])
            assert([len(x) for x in window.buckets] == lengths)


def test_AdaptiveWindow_item_counts():
    (item_count, _) = count_item_frequency_in(test_transactions)
    window = AdaptiveWindow(1, 1)
    # Note: map() produces a generator which can be evaluated only once,
    # so we need to force it to evaluate, otherwise it can't be stored in
    # the bucket list safely.
    for transaction in test_transactions:
        window.add(transaction)
    for item in item_count.keys():
        count = 0
        for bucket in window.buckets:
            count += bucket.tree.item_count[item]
        assert(count == item_count[item])
        count = sum([bucket.tree.item_count[item]
                     for bucket in window.buckets])
        assert(count == item_count[item])
