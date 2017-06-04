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
        self.count = count
        self.children = {}
        self.parent = parent

    def is_root(self):
        return self.parent is None

    def is_leaf(self):
        return len(self.children) == 0

    def __str__(self, level=0):
        ret = ("[root]" if self.is_root()
               else " " * level + str(self.item) + ":" + str(self.count))
        ret += "*" if self.is_leaf() else ""
        ret += "\n"
        for node in self.children.values():
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
                if node.is_leaf() and not node.is_root():
                    # Node was a leaf, but won't be after acquiring a child.
                    self.leaves.remove(node)
                child = FPNode(item, count, node)
                node.children[item] = child
                node = child
                self.leaves.add(node)
                if item not in self.header:
                    self.header[item] = set()
                self.header[item].add(node)
            else:
                node = node.children[item]
                node.count += count

    def sort(self):
        if LOG_TREE_MUTATIONS:
            print("Sorting tree")
        # To sort the tree, for each leaf in the tree, find the path to the
        # root, remove each such path, sort the path so that the items are
        # in non-increasing order order of frequency, and re-insert the
        # sorted path. The list of leaves can change while sorting; removing
        # a path may result in new leaves being created if the removed path
        # overlapped another path. We need to include the paths from these
        # new leaves in the sort too. The other way we create leaves while
        # sorting the tree is when we insert a sorted path; if not all items
        # overlap with other paths, we'll create a new leaf. The paths for
        # these leaves are sorted, so we don't need to include these paths
        # starting at such new leaves in the sort. So the set of leaves
        # changes while we're sorting the tree. Python can't iterate over
        # a mutating set, so we copy the list of leaves into a deque, and
        # push new leaves into that.
        leaves = deque(self.leaves)
        while len(leaves) > 0:
            leaf = leaves.pop()
            if not leaf.is_leaf():
                continue
            path = path_to_root(leaf)
            path.reverse()
            if len(path) == 0:
                continue
            spath = sort_transaction(path, self.item_count)
            if path == spath:
                # Path is already sorted.
                continue
            count = leaf.count
            new_leaves = self.remove(path, count)
            leaves.extend(new_leaves)
            self.insert(spath, count)

    def remove(self, path, count):
        # Removes a path of items from the tree. Returns list of newly created
        # leaves.
        if LOG_TREE_MUTATIONS:
            print("remove {} count {}".format(path, count))
        if len(path) == 0:
            return
        new_leaves = []
        parent = self.root
        for item in path:
            assert(item in parent.children)
            node = parent.children[item]
            assert(node.count >= count)
            node.count -= count
            self.item_count[node.item] -= count
            assert(node.count >= 0)
            if node.count == 0:
                del parent.children[item]
                if node.is_leaf():
                    self.leaves.remove(node)
                if parent.is_leaf() and parent.count > 0:
                    self.leaves.add(parent)
                    new_leaves += [parent]
                self.header[node.item].remove(node)
            parent = node
        self.num_transactions -= count
        assert(self.num_transactions >= 0)
        return new_leaves

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
    # For based on non-increasing item frequency. We need the sort to tie
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
