from adaptivewindow import AdaptiveWindow
from fptree import FPTree
from fptree import sort_transaction
from item import Item
from collections import Counter


def find_local_drift(window, local_cut, min_len):
    # Find the index in bucket list where local drift occurs; where
    # item frequencies change significantly.
    cut = 1
    while cut < len(window):
        # Create a Counter() for the item frequencies before and after the
        # cut point.
        prev_item_count = sum(
            [bucket.tree.item_count for bucket in window[0:cut]], Counter())
        curr_item_count = sum(
            [bucket.tree.item_count for bucket in window[cut:]], Counter())

        prev_len = sum([len(bucket) for bucket in window[0:cut]])
        curr_len = sum([len(bucket) for bucket in window[cut:]])

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
                                              global_cut,
                                              max_capacity,
                                              min_cut_len):
    assert(local_cut > 0 and local_cut <= 1)
    window = AdaptiveWindow(max_capacity)
    num_transactions = 0
    for transaction in [list(map(Item, t)) for t in transactions]:
        num_transactions += 1

        # Insert transaction into bucket list. Bucket list will merge
        # buckets as necessary to maintain exponential histogram.
        window.add(transaction)

        # Check for local drift, as the check is cheap.
        cut_index = find_local_drift(window, local_cut, min_cut_len)
        if cut_index is not None:
            window[0:cut_index] = []
        else:
            cut_index = find_global_drift(window, global_cut, min_cut_len)
            if cut_index is not None:
                window[0:cut_index] = []
