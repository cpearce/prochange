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

class FPNode:
    def __init__(self, item=None, count=0, parent=None):
        self.item = item
        self.count = count
        self.children = {}
        self.parent = parent

    def isRoot(self):
        return self.parent is None

    def __str__(self):
        return ("[" + str(self.item) + ":" + str(self.count) + "]->("
               + ','.join(map(lambda x: str(self.children[x]), self.children.keys()))
               + ")")


class FPTree:
    def __init__(self, item=None, count=0):
        self.root = FPNode()
        self.header = {}
        self.itemCount = Counter()
        self.numTransactions = 0

    def insert(self, transaction, count=1):
        node = self.root
        self.numTransactions += count
        for item in transaction:
            self.itemCount[item] += count
            if item not in node.children:
                child = FPNode(item, count, node)
                node.children[item] = child
                node = child
                if item not in self.header:
                    self.header[item] = []
                self.header[item] += [node]
            else:
                node = node.children[item]
                node.count += count

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

def ConstructInitialTree(transactions):
    frequency = Counter()
    for transaction in transactions:
        for item in map(Item, transaction):
            frequency[item] +=1
    tree = FPTree()
    for transaction in transactions:
        # sort by decreasing count.
        tree.insert(sorted(map(Item, transaction), key=lambda item:frequency[item], reverse=True))
    return tree

def TestFPTree():
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

    datasets = [
        ("datasets/BMS-POS.csv", 0.02),
        ("datasets/UCI-zoo.csv", 0.2),
        ("datasets/kosarak.csv", 0.01),
        ("datasets/mushroom.csv", 0.3),
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
    TestFPTree()
