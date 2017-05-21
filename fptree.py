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

class FPNode:
    def __init__(self, item=None, count=0, parent=None, generation=0):
        self.item = item
        self.count = count
        self.children = {}
        self.parent = parent
        self.generation = generation

    def isRoot(self):
        return self.parent is None

    def isLeaf(self):
        return len(self.children) == 0

    def __str__(self, level=0):
        ret = " "*level+str(self.item)+":" + str(self.count)
        ret += ("*" if self.isLeaf() else "")
        # ret += "[" + str(self.generation) + "]"
        ret += "\n"
        for node in self.children.values():
            ret += node.__str__(level+1)
        return ret

    # def __str__(self):
    #     return ("[" + str(self.item) + ":" + str(self.count) + "]->("
    #            + ','.join(map(lambda x: str(self.children[x]), self.children.keys()))
    #            + ")")
    def __repr__(self):
        return self.__str__()

class FPTree:
    def __init__(self, item=None):
        self.root = FPNode()
        self.header = {}
        self.itemCount = Counter()
        self.numTransactions = 0
        self.leaves = set()
        self.generation = 0

    def insert(self, transaction, count=1, generation=0):
        self.insertAt(transaction, count, self.root, generation)

    def insertAt(self, transaction, count, parent, generation):
        if DEBUG_ASSERTIONS:
            transaction = list(transaction)
            print("insert {} at {}".format(str(transaction), parent))
            assert(count > 0)
        node = parent
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

    def sort(self):
        # Tracks node which have sorted paths *above* them.
        is_sorted = set([self.root])
        # Make a copy, so that we don't lose leaves while modifying.
        leaves = deque(self.leaves)
        while len(leaves) > 0:
            leaf = leaves.pop();
            if not leaf.isLeaf():
                continue
            path = []
            node = leaf
            while not node in is_sorted:
                path += [node.item]
                node = node.parent
            path.reverse()
            # node is now the parent node of the path, below which the
            # remaining path is unsorted.
            if len(path) == 0:
                continue
            spath = SortTransaction(path, self.itemCount)
            if spath == path:
                # Path is already sorted. Add path's nodes to the set
                # of sorted nodes.
                n = leaf
                while n is not node:
                    assert(n not in is_sorted)
                    is_sorted.add(n)
                    n = n.parent
                continue
            count = leaf.count
            leaves.extend(self.remove(path, count, node))
            self.insertAt(spath, count, node)
            # Need to tag nodes as sorted.
        # assert(self.IsSorted())

    # returns new leaves!
    def remove(self, path, count, parent):
        if DEBUG_ASSERTIONS:
            print("remove {} at {} count {}".format(path, parent, count))
            assert(all(map(lambda x: x.isLeaf(), self.leaves)))
            assert(all(map(lambda x: x.count > 0, self.leaves)))
        if len(path) == 0:
            return
        node = None
        new_leaves = []
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
        return new_leaves         

    def IsSorted(self):
        for leaf in self.leaves:
            node = leaf
            while node.parent is not self.root:
                if self.itemCount[node.item] > self.itemCount[node.parent.item]:
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

def FPGrowth(tree, minCount, path):
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
    return FPGrowth(tree, mincount, [])

def SortTransaction(transaction, frequency):
    if not isinstance(frequency, Counter):
        raise TypeError("frequency must be Counter")
    return sorted(transaction, key=lambda item:frequency[item], reverse=True)    

def ConstructInitialTree(transactions):
    frequency = Counter()
    for transaction in transactions:
        for item in map(Item, transaction):
            frequency[item] +=1
    tree = FPTree()
    for transaction in transactions:
        # sort by decreasing count.
        tree.insert(SortTransaction(map(Item, transaction), frequency))
    return tree

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
        ("datasets/UCI-zoo.csv", 0.2),
        ("datasets/mushroom.csv", 0.3),
        ("datasets/BMS-POS.csv", 0.02),
        ("datasets/kosarak.csv", 0.01),
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
    BasicSanityTest()
    SortTest()
    #StressTest()
