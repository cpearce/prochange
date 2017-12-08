from fptree import FPTree
from fptree import mine_fp_tree
from item import Item
from collections import deque
from fptree import sort_transaction
from fptree import fp_growth
import sys

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")


def mine_cp_tree_stream(transactions, min_support, sort_interval, window_size):
    # Yields (window_start_index, window_length, patterns)
    tree = FPTree()
    sliding_window = deque()
    frequency = None
    num_transactions = 0
    for transaction in transactions:
        num_transactions += 1
        transaction = sort_transaction(transaction, frequency)
        tree.insert(transaction)
        sliding_window.append(transaction)
        if len(sliding_window) > window_size:
            transaction = sliding_window.popleft()
            transaction = sort_transaction(transaction, frequency)
            tree.remove(transaction, 1)
            assert(len(sliding_window) == window_size)
            assert(tree.num_transactions == window_size)
        if (num_transactions % sort_interval) == 0:
            tree.sort()
            frequency = tree.item_count.copy()
        if (num_transactions % window_size) == 0:
            if (num_transactions % sort_interval) != 0:
                # We won't have sorted due to the previous check, so we
                # need to sort before mining.
                tree.sort()
                frequency = tree.item_count.copy()
            assert(tree.num_transactions == len(sliding_window))
            assert(len(sliding_window) == window_size)
            min_count = min_support * tree.num_transactions
            patterns = set()
            supports = dict()
            fp_growth(
                tree,
                min_count,
                [],
                num_transactions,
                patterns,
                supports)
            yield (num_transactions - len(sliding_window), len(sliding_window), patterns, supports)
    else:
        # We didn't just mine on the last transaction, we need to mine now,
        # else we'll miss data.
        if (num_transactions % window_size) != 0:
            if (num_transactions % sort_interval) != 0:
                tree.sort()
                frequency = tree.item_count.copy()
            min_count = min_support * tree.num_transactions
            patterns = set()
            supports = dict()
            fp_growth(
                tree,
                min_count,
                [],
                num_transactions,
                patterns,
                supports)
            yield (num_transactions - len(sliding_window), len(sliding_window), patterns, supports)
