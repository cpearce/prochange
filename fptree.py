from collections import Counter
from collections import deque
from apriori import apriori
from index import InvertedIndex
from item import Item
from item import ItemSet
import time
import csv
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

    def has_single_path(self):
        node = self.root
        while node is not None:
            if len(node.children) > 1:
                return False
            elif len(node.children) == 0:
                return True
            node = first_child(node)

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


def patterns_in_path(tree, node, min_count, path):
    itemsets = []
    is_large = tree.item_count[node.item] >= min_count
    if is_large:
        itemsets += [frozenset(path + [node.item])]
    if len(node.children) > 0:
        child = first_child(node)
        if is_large:
            itemsets += patterns_in_path(tree,
                                         child,
                                         min_count,
                                         path + [node.item])
        itemsets += patterns_in_path(tree, child, min_count, path)
    return itemsets


def patterns_in_tree(tree, min_count, path):
    assert(tree.has_single_path())
    if len(tree.root.children) == 0:
        return []
    return patterns_in_path(tree, first_child(tree.root), min_count, path)


def fp_growth(tree, min_count, path):
    # If tree has only one branch, we can skip creating a tree and just add
    # all combinations of items in the branch.
    if tree.has_single_path():
        rv = patterns_in_tree(tree, min_count, path)
        return rv
    # For each item in the tree that is frequent, in increasing order
    # of frequency...
    itemsets = []
    for item in sorted(
            tree.item_count.keys(),
            key=lambda i: tree.item_count[i]):
        if tree.item_count[item] < min_count:
            # Item is no longer frequent on this path, skip.
            continue
        # Record item as part of the path.
        itemsets += [frozenset(path + [item])]
        # Build conditional tree of all patterns in this tree which start
        # with this item.
        conditional_tree = construct_conditional_tree(tree, item)
        itemsets += fp_growth(conditional_tree, min_count, path + [item])
    return itemsets


def mine_fp_tree(transactions, min_support):
    tree = construct_initial_tree(transactions)
    min_count = min_support * tree.num_transactions
    return fp_growth(tree, min_count, [])


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
    for transaction in transactions:
        for item in map(Item, transaction):
            frequency[item] += 1
    return frequency


def construct_initial_tree(transactions):
    frequency = count_item_frequency_in(transactions)
    tree = FPTree()
    for transaction in transactions:
        tree.insert(sort_transaction(map(Item, transaction), frequency))
    return tree
