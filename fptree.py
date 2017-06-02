from collections import Counter
from collections import deque
from apriori import Apriori
from index import InvertedIndex
from item import Item
from item import ItemSet
import time
import csv
import sys

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")

DEBUG_ASSERTIONS = False
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
        assert(self.is_leaves_list_sane())
        assert(self.is_connected())
        assert(self.header_list_sane())

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
        if DEBUG_ASSERTIONS:
            assert(self.is_sorted())
            assert(self.is_connected())
            assert(self.header_list_sane())

    def remove(self, path, count):
        # Removes a path of items from the tree. Returns list of newly created
        # leaves.
        assert(self.header_list_sane())
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
        assert(self.is_connected())
        assert(self.header_list_sane())
        assert(self.is_leaves_list_sane())
        return new_leaves

    def is_leaves_list_sane(self):
        # Ensure leaves are correctly tracked
        return (all(map(lambda x: x.is_leaf(), self.leaves)) and
                all(map(lambda x: x.count > 0, self.leaves)))

    def is_sorted(self):
        for leaf in self.leaves:
            node = leaf
            while node.parent is not self.root:
                if self.item_count[node.item] > self.item_count[node.parent.item]:
                    return False
                node = node.parent
        return True

    def is_connected(self):
        for leaf in self.leaves:
            node = leaf
            while node is not self.root:
                if node.item not in node.parent.children:
                    return False
                node = node.parent
        return True

    def header_list_sane(self):
        for (item, nodes) in self.header.items():
            for node in nodes:
                while not node.is_root():
                    if node.item not in node.parent.children:
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

# Yields (window_start_index, window_length, patterns)


def mine_cp_tree_stream(transactions, min_support, sort_interval, window_size):
    tree = FPTree()
    sliding_window = deque()
    frequency = None
    num_transactions = 0
    for transaction in transactions:
        num_transactions += 1
        transaction = sort_transaction(map(Item, transaction), frequency)
        tree.insert(transaction)
        sliding_window.append(transaction)
        did_sort = False
        if len(sliding_window) > window_size:
            transaction = sliding_window.popleft()
            transaction = sort_transaction(transaction, frequency)
            tree.remove(transaction, 1)
            assert(len(sliding_window) == window_size)
            assert(tree.num_transactions == window_size)
        if (num_transactions % sort_interval) == 0:
            tree.sort()
            assert(tree.is_sorted())
            assert(tree.is_connected())
            frequency = tree.item_count.copy()
            did_sort = True
        if (num_transactions % window_size) == 0:
            if not did_sort:
                tree.sort()
                frequency = tree.item_count.copy()
            min_count = min_support * tree.num_transactions
            assert(tree.num_transactions == len(sliding_window))
            assert(len(sliding_window) == window_size)
            assert(tree.is_sorted())
            assert(tree.is_connected())
            patterns = fp_growth(tree, min_count, [])
            yield (num_transactions - len(sliding_window), len(sliding_window), patterns)


def test_cp_tree_stream():
    # (csvFilePath, min_support, sort_interval, window_size)
    datasets = [
        ("datasets/UCI-zoo.csv", 0.3, 10, 20),
        ("datasets/mushroom.csv", 0.4, 500, 500),
        # ("datasets/BMS-POS.csv", 0.05, 50000, 50000),
    ]
    for (csvFilePath, min_support, sort_interval, window_size) in datasets:
        with open(csvFilePath, newline='') as csvfile:
            print("test_cp_tree_stream {}".format(csvFilePath))
            transactions = list(csv.reader(csvfile))
            print("Loaded data file, {} lines".format(len(transactions)))
            for (
                    window_start_index,
                    window_length,
                    cptree_itemsets) in mine_cp_tree_stream(
                    transactions,
                    min_support,
                    sort_interval,
                    window_size):
                print("Window {} + {} / {}".format(window_start_index,
                                                   window_size, len(transactions)))
                window = transactions[window_start_index:
                                      window_start_index + window_length]
                fptree_itemsets = mine_fp_tree(window, min_support)
                print(
                    "fptree produced {} itemsets, cptree produced {} itemsets".format(
                        len(fptree_itemsets),
                        len(cptree_itemsets)))
                assert(set(cptree_itemsets) == set(fptree_itemsets))


def test_basic_sanity():
    # Basic sanity check of know resuts.
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
    expected_itemsets = {
        ItemSet("e"), ItemSet("de"), ItemSet("ade"), ItemSet("ce"),
        ItemSet("ae"),

        ItemSet("d"), ItemSet("cd"), ItemSet("bcd"), ItemSet("acd"),
        ItemSet("bd"), ItemSet("abd"), ItemSet("ad"),

        ItemSet("c"), ItemSet("bc"), ItemSet("abc"), ItemSet("ac"),

        ItemSet("b"), ItemSet("ab"),

        ItemSet("a"),
    }

    itemsets = mine_fp_tree(transactions, 2 / len(transactions))
    assert(set(itemsets) == expected_itemsets)


def test_tree_sorting():
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

    expected_tree = construct_initial_tree(transactions)
    assert(expected_tree.is_sorted())

    tree = FPTree()
    for transaction in transactions:
        # Insert reversed, since lexicographical order is already decreasing
        # frequency order in this example.
        tree.insert(map(Item, reversed(transaction)))
    assert(str(expected_tree) != str(tree))
    tree.sort()
    assert(tree.is_sorted())
    assert(str(expected_tree) == str(tree))

    datasets = [
        "datasets/UCI-zoo.csv",
        "datasets/mushroom.csv",
        # "datasets/BMS-POS.csv",
        # "datasets/kosarak.csv",
    ]

    for csvFilePath in datasets:
        print("Loading FPTree for {}".format(csvFilePath))
        start = time.time()
        tree = FPTree()
        with open(csvFilePath, newline='') as csvfile:
            for line in list(csv.reader(csvfile)):
                # Insert sorted lexicographically
                transaction = sorted(map(Item, line))
                tree.insert(transaction)
        duration = time.time() - start
        print("Loaded in {:.2f} seconds".format(duration))
        print("Sorting...")
        start = time.time()
        tree.sort()
        duration = time.time() - start
        print("Sorting took {:.2f} seconds".format(duration))
        assert(tree.is_sorted())


def test_stress():
    datasets = [
        ("datasets/UCI-zoo.csv", 0.3),
        ("datasets/mushroom.csv", 0.4),
        # ("datasets/BMS-POS.csv", 0.05),
        # ("datasets/kosarak.csv", 0.05),
    ]

    for (csvFilePath, min_support) in datasets:
        # Run Apriori and FP-Growth and assert both have the same results.
        print("Running Apriori for {}".format(csvFilePath))
        start = time.time()
        index = InvertedIndex()
        index.loadCSV(csvFilePath)
        apriori_itemsets = Apriori(index, min_support)
        apriori_duration = time.time() - start
        print(
            "Apriori complete. Generated {} itemsets in {:.2f} seconds".format(
                len(apriori_itemsets),
                apriori_duration))

        print("Running FPTree for {}".format(csvFilePath))
        start = time.time()
        with open(csvFilePath, newline='') as csvfile:
            transactions = list(csv.reader(csvfile))
            fptree_itemsets = mine_fp_tree(transactions, min_support)
        fptree_duration = time.time() - start
        print(
            "fp_growth complete. Generated {} itemsets in {:.2f} seconds".format(
                len(fptree_itemsets),
                fptree_duration))

        if set(fptree_itemsets) == set(apriori_itemsets):
            print("SUCCESS({}): Apriori and fptree results match".format(csvFilePath))
        else:
            print("FAIL({}): Apriori and fptree results differ!".format(csvFilePath))
        assert(set(fptree_itemsets) == set(apriori_itemsets))

        if apriori_duration > fptree_duration:
            print(
                "FPTree was faster by {:.2f} seconds".format(
                    apriori_duration -
                    fptree_duration))
        else:
            print(
                "Apriori was faster by {:.2f} seconds".format(
                    fptree_duration -
                    apriori_duration))
        print("")


if __name__ == "__main__":
    test_basic_sanity()
    test_tree_sorting()
    test_stress()
    test_cp_tree_stream()
