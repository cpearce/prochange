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

DEBUG_ASSERTIONS = True
LOG_TREE_MUTATIONS = False

class FPNode:
    def __init__(self, item=None, count=0, parent=None):
        self.item = item
        self.count = count
        self.children = {}
        self.parent = parent

    def isRoot(self):
        return self.parent is None

    def isLeaf(self):
        return len(self.children) == 0

    def __str__(self, level=0):
        ret = ("[root]" if self.isRoot()
            else " " * level + str(self.item) + ":" + str(self.count))
        ret += "*" if self.isLeaf() else ""
        ret += "\n"
        for node in self.children.values():
            ret += node.__str__(level+1)
        return ret

    def __repr__(self):
        return self.__str__()

class FPTree:
    def __init__(self, item=None):
        self.root = FPNode()
        self.header = {}
        self.itemCount = Counter()
        self.numTransactions = 0
        self.leaves = set()

    def insert(self, transaction, count=1):
        if DEBUG_ASSERTIONS:
            transaction = list(transaction)
            assert(count > 0)
        if LOG_TREE_MUTATIONS:
            print("insert {} count {}".format(transaction, count))
        node = self.root
        self.numTransactions += count
        for item in transaction:
            self.itemCount[item] += count
            if item not in node.children:
                if node.isLeaf() and not node.isRoot():
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
        if DEBUG_ASSERTIONS:
            # Ensure leaves are correctly tracked
            assert(all(map(lambda x: x.isLeaf(), self.leaves)))
            assert(all(map(lambda x: x.count > 0, self.leaves)))
            assert(self.IsConnected())
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
        n = self.numTransactions
        f = self.itemCount.copy()
        while len(leaves) > 0:
            leaf = leaves.pop();
            if not leaf.isLeaf():
                continue
            path = PathToRoot(leaf)
            path.reverse()
            if len(path) == 0:
                continue
            spath = SortTransaction(path, self.itemCount)
            if path == spath:
                # Path is already sorted.
                continue
            count = leaf.count
            new_leaves = self.remove(path, count)
            leaves.extend(new_leaves)
            self.insert(spath, count)
        assert(n == self.numTransactions)
        assert(f == self.itemCount)
        if DEBUG_ASSERTIONS:
            assert(self.IsSorted())
            assert(self.IsConnected())
            assert(self.header_list_sane())


    def remove(self, path, count):
        # Removes a path of items from the tree. Returns list of newly created
        # leaves.
        if DEBUG_ASSERTIONS:
            assert(all(map(lambda x: x.isLeaf(), self.leaves)))
            assert(all(map(lambda x: x.count > 0, self.leaves)))
        if LOG_TREE_MUTATIONS:
            print("remove {} count {}".format(path, count))
        if len(path) == 0:
            return
        node = None
        new_leaves = []
        parent = self.root
        for item in path:
            assert(item in parent.children)
            node = parent.children[item]
            assert(node.count >= count)
            node.count -= count
            self.itemCount[node.item] -= count
            assert(node.count >= 0)
            if node.count == 0:
                del parent.children[item]
                if node.isLeaf():
                    self.leaves.remove(node)
                if parent.isLeaf() and parent.count > 0:
                    self.leaves.add(parent)
                    new_leaves += [parent]
                self.header[node.item].remove(node)
                # Ensure leaves are correctly tracked
                if DEBUG_ASSERTIONS:
                    assert(all(map(lambda x: x.isLeaf(), self.leaves)))
                    assert(all(map(lambda x: x.count > 0, self.leaves)))
            parent = node
        self.numTransactions -= count
        assert(self.numTransactions >= 0)
        assert(self.IsConnected())
        assert(self.header_list_sane())
        return new_leaves         

    def IsSorted(self):
        is_sorted = True
        for leaf in self.leaves:
            node = leaf
            while node.parent is not self.root:
                if node.item not in node.parent.children:
                    print("Node {} is not in parent!".format(node))
                if self.itemCount[node.item] > self.itemCount[node.parent.item]:
                    print("Not sorted! node={},{} parent={},{}".format(node.item, self.itemCount[node.item], node.parent.item, self.itemCount[node.parent.item]))
                    # return False
                    is_sorted = False
                node = node.parent
        return is_sorted

    def IsConnected(self):
        is_connected = True
        for leaf in self.leaves:
            node = leaf
            while node is not self.root:
                if node.item not in node.parent.children:
                    print("Node {} is not in parent {} (children={})!".format(node, node.parent, node.parent.children))
                    is_connected = False
                node = node.parent
        return is_connected        

    def header_list_sane(self):
        for (item, nodes) in self.header.items():
            for node in nodes:
                while not node.isRoot():
                    if node.item not in node.parent.children:
                        return False
                    node = node.parent
        return True

    def hasSinglePath(self):
        node = self.root
        while node is not None:
            if len(node.children) > 1:
                return False
            elif len(node.children) == 0:
                return True
            node = FirstChild(node)

    def __str__(self):
        return "(" + str(self.root) + ")"

def PathToRoot(node):
    path = []
    while not node.isRoot():
        path += [node.item]
        node = node.parent
    return path

def ConstructConditionalTree(tree, item):
    conditionalTree = FPTree()
    for node in tree.header[item]:
        path = PathToRoot(node.parent)
        conditionalTree.insert(reversed(path), node.count)
    return conditionalTree

def FirstChild(node):
    return list(node.children.values())[0]

def PatternsInPath(tree, node, minCount, path):
    itemsets = []
    isLarge = tree.itemCount[node.item] >= minCount
    if isLarge:
        itemsets += [frozenset(path + [node.item])]
    if len(node.children) > 0:
        child = FirstChild(node)
        if isLarge:
            itemsets += PatternsInPath(tree, child, minCount, path + [node.item])
        itemsets += PatternsInPath(tree, child, minCount, path)
    return itemsets

def PatternsInTree(tree, minCount, path):
    assert(tree.hasSinglePath())
    if len(tree.root.children) == 0:
        return []
    return PatternsInPath(tree, FirstChild(tree.root), minCount, path);

def FPGrowth(tree, minCount, path=[]):
    # If tree has only one branch, we can skip creating a tree and just add
    # all combinations of items in the branch.
    if tree.hasSinglePath():
        rv = PatternsInTree(tree, minCount, path);
        return rv
    # For each item in the tree that is frequent, in increasing order
    # of frequency...
    itemsets = []
    for item in sorted(tree.itemCount.keys(), key=lambda item:tree.itemCount[item]):
        if tree.itemCount[item] < minCount:
            # Item is no longer frequent on this path, skip.
            continue
        # Record item as part of the path.
        itemsets += [frozenset(path + [item])]
        # Build conditional tree of all patterns in this tree which start
        # with this item.
        conditionalTree = ConstructConditionalTree(tree, item)
        itemsets += FPGrowth(conditionalTree, minCount, path + [item])
    return itemsets

def MineFPTree(transactions, minsup):
    tree = ConstructInitialTree(transactions)
    mincount = minsup * tree.numTransactions
    return FPGrowth(tree, mincount)

def SortTransaction(transaction, frequency):
    if frequency is None:
        return sorted(transaction)
    if not isinstance(frequency, Counter):
        raise TypeError("frequency must be Counter")
    return sorted(transaction, key=lambda item:frequency[item], reverse=True)    

def CountItemFrequencyIn(transactions):
    frequency = Counter()
    for transaction in transactions:
        for item in map(Item, transaction):
            frequency[item] += 1
    return frequency

def ConstructInitialTree(transactions):
    frequency = CountItemFrequencyIn(transactions)
    tree = FPTree()
    for transaction in transactions:
        # sort by decreasing count.
        tree.insert(SortTransaction(map(Item, transaction), frequency))
    return tree

# Returns (window_start_index, window_length, patterns)
def MineCPTreeStream(transactions, minsup, sort_interval, window_size):
    tree = FPTree()
    sliding_window = deque();
    frequency = None
    num_transactions = 0
    for transaction in transactions:
        num_transactions += 1
        transaction = SortTransaction(map(Item, transaction), frequency)
        tree.insert(transaction)
        sliding_window.append(transaction)
        did_sort = False
        if len(sliding_window) > window_size:
            transaction = sliding_window.popleft()
            transaction = SortTransaction(transaction, frequency)
            tree.remove(transaction)
            assert(len(sliding_window) == window_size)
            assert(tree.numTransactions == window_size)
        if (num_transactions % sort_interval) == 0:
            print("Sorting tree at {}".format(num_transactions))
            tree.sort()
            assert(tree.IsSorted())
            assert(tree.IsConnected())
            frequency = tree.itemCount.copy()
            did_sort = True
        if (num_transactions % window_size) == 0:
            if not did_sort:
                tree.sort()
                frequency = tree.itemCount.copy()
            mincount = minsup * tree.numTransactions
            assert(tree.numTransactions == len(sliding_window))
            assert(len(sliding_window) == window_size)
            assert(tree.IsSorted())
            assert(tree.IsConnected())
            patterns = FPGrowth(tree, mincount)
            yield (num_transactions - len(sliding_window), len(sliding_window), patterns)

def CPTreeTest():
    # (csvFilePath, minsup, sort_interval, window_size)
    datasets = [
        ("datasets/UCI-zoo.csv", 0.3, 5, 10),
        ("datasets/mushroom.csv", 0.4, 1000, 1000),
        ("datasets/BMS-POS.csv", 0.05, 50000, 50000),
        # ("datasets/kosarak.csv", 0.05),
    ]
    for (csvFilePath, minsup, sort_interval, window_size) in datasets:
        with open(csvFilePath, newline='') as csvfile:
            print("CPTreeTest {}".format(csvFilePath))
            transactions = list(csv.reader(csvfile))
            for (window_start_index, window_length, cptree_itemsets) in MineCPTreeStream(transactions, minsup, sort_interval, window_size):
                print("Window {} + {} / {}".format(window_start_index, window_size, len(transactions)))
                window = transactions[window_start_index:window_start_index + window_length];
                fptree_itemsets = MineFPTree(window, minsup)
                print("fptree={} cptree={}".format(len(fptree_itemsets), len(cptree_itemsets)))
                assert(set(cptree_itemsets) == set(fptree_itemsets))

        
def BasicSanityTest():
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
    expectedItemsets = set([
        ItemSet("e"), ItemSet("de"), ItemSet("ade"), ItemSet("ce"),
        ItemSet("ae"),

        ItemSet("d"), ItemSet("cd"), ItemSet("bcd"), ItemSet("acd"),
        ItemSet("bd"), ItemSet("abd"), ItemSet("ad"),

        ItemSet("c"), ItemSet("bc"), ItemSet("abc"), ItemSet("ac"),

        ItemSet("b"), ItemSet("ab"),

        ItemSet("a"),
    ])

    itemsets = MineFPTree(transactions, 2 / len(transactions))
    assert(set(itemsets) == expectedItemsets)

def SortTest():
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

    print("Loading expected tree");
    expectedTree = ConstructInitialTree(transactions)
    assert(expectedTree.IsSorted())

    print("Loading sort tree");
    tree = FPTree()
    for transaction in transactions:
        # Insert reversed, since lexicographical order is already decreasing
        # frequency order in this example.
        tree.insert(map(Item, reversed(transaction)))
    assert(str(expectedTree) != str(tree))

    print("\nTree before sort {}\n".format(tree))

    print("\nSorting tree");
    tree.sort()
    print("\nObserved {}\n".format(tree))

    print("\nExpected {}\n".format(expectedTree))

    assert(tree.IsSorted())
    assert(str(expectedTree) == str(tree))

    datasets = [
        "datasets/UCI-zoo.csv",
        "datasets/mushroom.csv",
        "datasets/BMS-POS.csv",
        "datasets/kosarak.csv",
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
        assert(tree.IsSorted())

def StressTest():
    datasets = [
        ("datasets/UCI-zoo.csv", 0.3),
        ("datasets/mushroom.csv", 0.4),
        ("datasets/BMS-POS.csv", 0.05),
        ("datasets/kosarak.csv", 0.05),
    ]

    for (csvFilePath, minsup) in datasets:
        # Run Apriori and FP-Growth and assert both have the same results.
        print("Running Apriori for {}".format(csvFilePath))
        start = time.time()
        index = InvertedIndex();
        index.loadCSV(csvFilePath)
        apriori_itemsets = Apriori(index, minsup)
        apriori_duration = time.time() - start
        print("Apriori complete. Generated {} itemsets in {:.2f} seconds".format(len(apriori_itemsets), apriori_duration))

        print("Running FPTree for {}".format(csvFilePath))
        start = time.time()
        fptree_itemsets = []
        with open(csvFilePath, newline='') as csvfile:
            transactions = list(csv.reader(csvfile))
            fptree_itemsets = MineFPTree(transactions, minsup)
        fptree_duration = time.time() - start
        print("FPGrowth complete. Generated {} itemsets in {:.2f} seconds".format(len(fptree_itemsets), fptree_duration))

        if set(fptree_itemsets) == set(apriori_itemsets):
            print("SUCCESS({}): Apriori and fptree results match".format(csvFilePath))
        else:
            print("FAIL({}): Apriori and fptree results differ!".format(csvFilePath))

        if apriori_duration > fptree_duration:
            print("FPTree was faster by {:.2f} seconds".format(apriori_duration - fptree_duration))
        else:
            print("Apriori was faster by {:.2f} seconds".format(fptree_duration - apriori_duration))
        print("")

if __name__ == "__main__":
    # BasicSanityTest()
    # SortTest()
    # StressTest()
    CPTreeTest();
    