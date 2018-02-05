from adaptivewindow import AdaptiveWindow
from fptree import FPTree
from fptree import sort_transaction
from hoeffdingbound import hoeffding_bound
from item import Item
from collections import Counter
import math
import sys

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")


def build_tree(window, item_count):
    path_len_sum = 0
    path_count = 0
    tree = FPTree()
    for bucket in window:
        for (transaction, count) in bucket.tree:
            sorted_transaction = sort_transaction(
                transaction, item_count)
            path_len_sum += count * len(sorted_transaction)
            path_count += count
            tree.insert(sorted_transaction, count)
    avg_path_len = path_len_sum / path_count
    return (tree, avg_path_len)


def find_concept_drift(
        window,
        min_cut_len,
        local_cut_confidence):
    # Find the index in bucket list where local drift occurs.
    if len(window) < 2:
        # Only one or less buckets, can't have drift.
        return (None, None)

    cut_index = len(window) - 2
    while cut_index >= 0:
        before_len = sum([len(bucket) for bucket in window[0:cut_index]])
        after_len = sum([len(bucket) for bucket in window[cut_index:]])

        # Ensure the candidate cut is a non-trivial length.
        if before_len < min_cut_len or after_len < min_cut_len:
            cut_index -= 1
            continue

        # Create a Counter() for the item frequencies before and after the
        # cut point.
        before_item_count = sum(
            [bucket.tree.item_count for bucket in window[0:cut_index]], Counter())
        after_item_count = sum(
            [bucket.tree.item_count for bucket in window[cut_index:]], Counter())

        # Check if any item's frequency has a significant difference.
        for item in after_item_count.keys():
            before_support = before_item_count[item] / before_len
            after_support = after_item_count[item] / after_len
            if not hoeffding_bound(
                    before_support,
                    before_len,
                    after_support,
                    after_len,
                    local_cut_confidence):
                # Supports differ; local drift.
                # Build tree to return to the mining algorithm.
                (tree, _) = build_tree(
                    window[cut_index:], after_item_count)
                return (cut_index, tree)

        cut_index -= 1
    return (None, None)


def change_detection_transaction_data_streams(transactions,
                                              window_len,
                                              merge_threshold,
                                              min_cut_len,
                                              local_cut_confidence):
    assert(local_cut_confidence > 0 and local_cut_confidence <= 1)
    window = AdaptiveWindow(window_len, merge_threshold)
    num_transaction = 0
    for transaction in transactions:
        num_transaction += 1

        # Insert transaction into bucket list. Bucket list will merge
        # buckets as necessary to maintain exponential histogram.
        if not window.add(transaction):
            # Not at a adaptive window bucket boundary.
            continue

        # At a adaptive window bucket boundary. Check for concept drift.
        (cut_index, tree) = find_concept_drift(
            window,
            min_cut_len,
            local_cut_confidence)
        if cut_index is None:
            continue

        # Otherwise we have concept drift, need to drop and mine.
        window[0:cut_index] = []
        yield (tree, num_transaction)
