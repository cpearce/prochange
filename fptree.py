from collections import Counter
from collections import deque
from item import Item
from item import ItemSet
import time
import sys

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")

LOG_TREE_MUTATIONS = False


class FPNode:
    def __init__(self, item=None, count=0, parent=None):
        self.item = item
        # Number of paths which include this node.
        self.count = count
        # Number of paths which end on this node. There may be other paths
        # for which the path down to this node is a prefix.
        self.end_count = 0
        self.children = {}
        self.parent = parent

    def is_root(self):
        return self.parent is None

    def is_leaf(self):
        return self.end_count > 0

    def __str__(self, level=0):
        ret = ("[root]" if self.is_root()
               else " " * level + str(self.item) + ":" + str(self.count))
        ret += "*" if self.is_leaf() else ""
        ret += "\n"
        # Print out the child nodes in decreasing order of count, tie break on
        # lexicographical order. As with sort_transaction() below, we achieve
        # this by relying on the fact that python's sort is stable, so we
        # sort first lexicographically, and again by count.
        children = sorted(self.children.values(), key=lambda node: node.item)
        children = sorted(children, key=lambda node: node.count, reverse=True)
        for node in children:
            ret += node.__str__(level + 1)
        return ret

    def __repr__(self):
        return self.__str__()


class FPTree:
    def __init__(self):
        self.root = FPNode()
        self.header = {}
        self.item_count = Counter()
        self.num_transactions = 0
        self.leaves = set()

    def insert(self, transaction, count=1):
        assert(count > 0)
        if LOG_TREE_MUTATIONS:
            transaction = list(transaction)
            print("insert {} count {}".format(transaction, count))
        node = self.root
        self.num_transactions += count
        for item in transaction:
            self.item_count[item] += count
            if item not in node.children:
                child = FPNode(item, count, node)
                node.children[item] = child
                node = child
                if item not in self.header:
                    self.header[item] = set()
                self.header[item].add(node)
            else:
                node = node.children[item]
                node.count += count
        node.end_count += count
        self.leaves.add(node)

    def sort(self):
        if LOG_TREE_MUTATIONS:
            print("Sorting tree")
        # To sort the tree, for each transaction's 'path' in the tree,
        # remove each such path, sort the path so that the items are
        # in non-decreasing order of frequency, and re-insert the
        # sorted path.
        #
        # The set of leaves changes while sorting; removing a path may
        # require a leaf node to be removed if there are no paths which
        # have this path as their prefix still in the tree. When the sorted
        # path is re-inserted, a new leaf for the end of the path may be
        # inserted too. Python can't iterate over its built-in set if it
        # mutates, so our iterator makes a copy of the set of leaves.
        for (path, count) in self:
            assert(len(path) > 0)
            sorted_path = sort_transaction(path, self.item_count)
            if path == sorted_path:
                # Path doesn't need to change.
                continue
            # 'count' is the number of instances of this path in the tree.
            # Note that there may be paths which have this path as their
            # prefix, i.e. the last node in the path may have children.
            self.remove(path, count)
            self.insert(sorted_path, count)

    def remove(self, path, count):
        # Removes a path of items from the tree.
        if LOG_TREE_MUTATIONS:
            print("remove {} count {}".format(path, count))
        assert(len(path) > 0)
        assert(count > 0)
        node = self.root
        for item in path:
            assert(item in node.children)
            child = node.children[item]
            assert(child.count >= count)
            child.count -= count
            self.item_count[child.item] -= count
            assert(child.count >= 0)
            if child.count == 0:
                del node.children[item]
                self.header[child.item].remove(child)
            node = child
        assert(node.end_count >= count)
        node.end_count -= count
        self.leaves.remove(node)
        self.num_transactions -= count
        assert(self.num_transactions >= 0)

    def is_sorted(self):
        for leaf in self.leaves:
            node = leaf
            while node.parent is not self.root:
                if self.item_count[node.item] > self.item_count[node.parent.item]:
                    return False
                node = node.parent
        return True

    def __str__(self):
        return "(" + str(self.root) + ")"

    def __iter__(self):
        # Iterates over (transaction,count), where transaction is
        # in root-to-leaf order.
        return [(list(reversed(path_to_root(node))), node.end_count)
                for node in self.leaves.copy()].__iter__()


def path_to_root(node):
    path = []
    while not node.is_root():
        path += [node.item]
        node = node.parent
    return path


def construct_conditional_tree(tree, item):
    conditional_tree = FPTree()
    for node in tree.header[item]:
        path = path_to_root(node.parent)
        conditional_tree.insert(reversed(path), node.count)
    return conditional_tree


def first_child(node):
    return list(node.children.values())[0]


def fp_growth(
        tree,
        min_count,
        path,
        path_count,
        itemsets,
        itemset_counts,
        maximal_only=False):
    # For each item in the tree that is frequent, in increasing order
    # of frequency...
    for item in sorted(
            tree.item_count.keys(),
            key=lambda i: tree.item_count[i]):
        if tree.item_count[item] < min_count:
            # Item is no longer frequent on this path, skip.
            continue

        # Need to store the support of this itemset, so we
        # can look it up during rule generation later on.
        itemset = frozenset(path + [item])
        new_path_count = min(path_count, tree.item_count[item])
        assert(itemset not in itemset_counts)
        itemset_counts[itemset] = new_path_count

        # Build conditional tree of all patterns in this tree which start
        # with this item.
        conditional_tree = construct_conditional_tree(tree, item)
        num_itemsets = len(itemsets)
        fp_growth(
            conditional_tree,
            min_count,
            path + [item],
            new_path_count,
            itemsets,
            itemset_counts,
            maximal_only)

        # Add the path to here to the output set, if appropriate.
        # If recursing further didn't yield any more itemsets, then
        # this is a maximal itemset.
        if not maximal_only or len(itemsets) == num_itemsets:
            itemsets.add(itemset)


def mine_fp_tree(transactions, min_support, maximal_itemsets_only=False):
    (tree, num_transactions) = construct_initial_tree(transactions, min_support)
    min_count = min_support * num_transactions
    itemsets = set()
    itemset_counts = dict()
    fp_growth(
        tree,
        min_count,
        [],
        num_transactions,
        itemsets,
        itemset_counts,
        maximal_itemsets_only)
    return (itemsets, itemset_counts, num_transactions)


def sort_transaction(transaction, frequency):
    # Sorts by non-increasing item frequency. We need the sort to tie
    # break consistently; so that when two items have the same frequency,
    # we always sort them into the same order. This is so that when we're
    # sorting the trees and we re-insert sorted paths, that the path
    # overlap in a consistent way. We achieve this ordering by sorting
    # twice; once lexicographically, and then a second time in order of
    # frequency. This works because Python's sort is stable; items that
    # compare equal aren't permuted.
    transaction = sorted(transaction)
    if frequency is None:
        return transaction
    if not isinstance(frequency, Counter):
        raise TypeError("frequency must be Counter")
    return sorted(transaction, key=lambda item: frequency[item], reverse=True)


def count_item_frequency_in(transactions):
    frequency = Counter()
    num_transactions = 0
    for transaction in transactions:
        num_transactions += 1
        for item in transaction:
            frequency[item] += 1
    return (frequency, num_transactions)


def construct_initial_tree(transactions, min_support):
    (frequency, num_transactions) = count_item_frequency_in(transactions)
    min_count = num_transactions * min_support
    tree = FPTree()
    for transaction in transactions:
        # Remove infrequent items from transaction. They cannot contribute to
        # producing frequent itemsets, and just slow down the tree algorithms.
        transaction = filter(
            lambda item: frequency[item] >= min_count,
            transaction)
        tree.insert(sort_transaction(transaction, frequency))
    return (tree, num_transactions)
