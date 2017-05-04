from collections import Counter

class FPNode:
    def __init__(self, item=None, count=0, parent=None):
        self.item = item
        self.count = count
        self.children = {}
        self.parent = parent
    def __str__(self):
        return ("[" + str(self.item) + ":" + str(self.count) + "]->("
               + ','.join(map(lambda x: str(self.children[x]), self.children.keys()))
               + ")")

class FPTree:
    def __init__(self, item=None, count=0):
        self.root = FPNode()
        self.header = {}

    def insert(self, transaction):
        node = self.root
        for item in transaction:
            if item not in node.children:
                child = FPNode(item, 1, node)
                node.children[item] = child
                node = child
                if item not in self.header:
                    self.header[item] = []
                self.header[item] += [node]
            else:
                node = node.children[item]
                node.count += 1

    def __str__(self):
        return "(" + str(self.root) + ")"


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
    frequency = Counter()
    for transaction in transactions:
        for item in transaction:
            frequency[item] +=1

    tree = FPTree()
    for transaction in transactions:
        # sort by decreasing count.
        tree.insert(sorted(transaction, key=lambda item:frequency[item], reverse=True))

    print(str(tree))

    print("header list:")
    for item in tree.header.keys():
        print("item:" + item)
        for node in tree.header[item]:
            path = []
            while node is not None:
                path.append("(" + str(node.item) + ":" + str(node.count) + ")")
                node = node.parent
            print(",".join(path))


if __name__ == "__main__":
    TestFPTree()
