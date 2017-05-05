from collections import Counter
from collections import deque

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
        path += node.item
        node = node.parent
    return path

def ConstructConditionalTree(tree, item):
    conditionalTree = FPTree()
    for node in tree.header[item]:
        path = PathToRoot(node.parent)
        print("path for {0}={1}".format(item, path))
        conditionalTree.insert(reversed(path), node.count)
    return conditionalTree

def FPGrowth(tree, minCount, path):
    itemsets = []
    if tree.hasSinglePath():
        #print("has single path")
        #return Patter
        # TODO: Seems this is unnecesary
        pass
    # foreach item in the header table that is frequent
    for item in sorted(tree.itemCount.keys(), key=lambda item:tree.itemCount[item]):
        print("FPGrowth item={} path={} count={}".format(item, path, tree.itemCount[item]))
        if tree.itemCount[item] < minCount:
            # print("insufficient count for {}".format(item))
            continue
        itemsets += [path + [item]]
        conditionalTree = ConstructConditionalTree(tree, item)
        print("conditional tree for item={} path={} is {}".format(item, path, conditionalTree))
        itemsets += FPGrowth(conditionalTree, minCount, path + [item])
    return itemsets


def MineFPTree(transactions, minsup):
    tree = ConstructInitialTree(transactions)
    mincount = minsup * tree.numTransactions
    return FPGrowth(tree, mincount, [])

def ConstructInitialTree(transactions):
    frequency = Counter()
    for transaction in transactions:
        for item in transaction:
            frequency[item] +=1
    tree = FPTree()
    for transaction in transactions:
        # sort by decreasing count.
        tree.insert(sorted(transaction, key=lambda item:frequency[item], reverse=True))
    return tree

def TestFPTree():
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
    # TODO: Can I flatten transactions somehow, and pass to Counter constructor?
    tree = ConstructInitialTree(transactions)
    print(str(tree))

    itemsets = MineFPTree(transactions, 2 / len(transactions))
    print("Itemsets={}".format(itemsets))

    # print("header list:")
    # for item in tree.header.keys():
    #     print("item:" + item)
    #     for node in tree.header[item]:
    #         path = []
    #         while node is not None:
    #             path.append("(" + str(node.item) + ":" + str(node.count) + ")")
    #             node = node.parent
    #         print(",".join(path))


if __name__ == "__main__":
    TestFPTree()
