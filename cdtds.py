from adaptivewindow import AdaptiveWindow
from editdistance import eval as levenstein_distance
from fptree import FPTree
from fptree import sort_transaction
from item import Item
from collections import Counter
import math


def tree_global_change(tree, other_item_count):
    assert(tree.is_sorted())
    change = 0.0
    for (path, count) in tree:
        sorted_path = sort_transaction(path, other_item_count)
        distance = levenstein_distance(path, sorted_path)
        change += (distance ** 2) / (len(path) ** 2)
    return change / tree.num_transactions


def variance(count, n):
    # Variance is defined as 1/n * E[(x-mu)^2]. We consider our X to be a
    # stream of n instances of [0,1] values; 1 if item appears in a transaction,
    # 0 if not. We know that the average is count/n, and that X is 1
    # count times, and 0 (n-count) times, so the variance then becomes:
    # 1/n * (count * (1 - support)^2 + (n-count) * (0 - support)^2).
    support = count / n
    return (count * (1 - support)**2 + (n - count) * (0 - support)**2) / n


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
        local_cut_confidence,
        global_cut_confidence):
    # Find the index in bucket list where local or global drift occurs.
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

        # First, detect local drift; a change in item frequencies.

        # Create a Counter() for the item frequencies before and after the
        # cut point.
        before_item_count = sum(
            [bucket.tree.item_count for bucket in window[0:cut_index]], Counter())
        after_item_count = sum(
            [bucket.tree.item_count for bucket in window[cut_index:]], Counter())

        # Check if any item's frequency has a significant difference.
        for item in after_item_count.keys():
            # Calculate "e local cut".
            n = before_item_count[item] + after_item_count[item]
            v = variance(n, before_len + after_len)
            m = 1 / ((1 / before_len) + 1 / after_len)
            delta_prime = local_cut_confidence / (before_len + after_len)
            epsilon = (math.sqrt(2 / n * v * math.log(2 / delta_prime))
                       + 2 / 3 * m * math.log(2 / delta_prime))

            before_support = before_item_count[item] / before_len
            after_support = after_item_count[item] / after_len
            if abs(before_support -
                   after_support) >= epsilon:
                # Local drift.
                # Build tree to return to the mining algorithm.
                (tree, avg_path_len) = build_tree(
                    window[cut_index:], after_item_count)
                return (cut_index, tree)

        # Check for global drift; new cooccurrences of items, but the
        # item frequencies not necessarily changing.

        # Create a new tree for the right hand side, sorted by the item
        # counts of the right hand side. This should have roughly the same
        # time complexity as sorting a tree of the same size.
        (tree, avg_path_len) = build_tree(window[cut_index:], after_item_count)
        num_paths_in_prev_tree = sum(
            [bucket.tree.num_transactions for bucket in window[0:cut_index]])

        # Calculate "e global cut"
        epsilon = (
            ((1 - global_cut_confidence) * (avg_path_len ** 2))
            / 6 * avg_path_len * num_paths_in_prev_tree)

        if tree_global_change(tree, after_item_count) > epsilon:
            # Global change.
            return (cut_index, tree)

        cut_index -= 1
    return (None, None)


def change_detection_transaction_data_streams(transactions,
                                              merge_threshold,
                                              min_cut_len,
                                              local_cut_confidence,
                                              global_cut_confidence):
    assert(local_cut_confidence > 0 and local_cut_confidence <= 1)
    assert(global_cut_confidence > 0 and global_cut_confidence <= 1)
    window = AdaptiveWindow(32, merge_threshold)
    num_transaction = 0
    for transaction in [list(map(Item, t)) for t in transactions]:
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
            local_cut_confidence,
            global_cut_confidence)
        if cut_index is None:
            continue

        # Otherwise we have concept drift, need to drop and mine.
        window[0:cut_index] = []
        yield (tree, num_transaction)
