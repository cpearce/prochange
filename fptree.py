from collections import Counter
from collections import deque
from apriori import Apriori
from index import InvertedIndex
from item import Item
from item import ItemSet
import csv

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
            node = list(node.children.values())[0]

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

def FPGrowth(tree, minCount, path):
    itemsets = []
    # if tree.hasSinglePath():
        #print("has single path")
        #return Patter
        # TODO: Seems this is unnecesary
        # pass
    # foreach item in the header table that is frequent
    for item in sorted(tree.itemCount.keys(), key=lambda item:tree.itemCount[item]):
        if tree.itemCount[item] < minCount:
            continue
        itemsets += [frozenset(path + [item])]
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

    # Run Apriori and FP-Growth and assert both have the same results.
    minsup = 0.3
    csvFilePath = "UCI-zoo.csv"

    index = InvertedIndex();
    index.loadCSV(csvFilePath)
    apriori_zoo = Apriori(index, minsup)
    print("Apriori complete. generated {} itemsets".format(len(apriori_zoo)))

    fp_zoo = []
    with open(csvFilePath, newline='') as csvfile:
        transactions = list(csv.reader(csvfile))
        fp_zoo = MineFPTree(transactions, minsup)

    print("FPGrowth complete. generated {} itemsets".format(len(fp_zoo)))

    assert(set(fp_zoo) == set(apriori_zoo))

if __name__ == "__main__":
    TestFPTree()
