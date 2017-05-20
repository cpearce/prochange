import csv
from item import Item
import sys

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")

class InvertedIndex:
    def __init__(self):
        self.index = dict()
        self.numTransactions = 0

    def _add(self, transaction):
        self.numTransactions += 1
        for item in transaction:
            if not isinstance(item, Item):
                raise TypeError("Item name must be Item")
            if item not in self.index:
                self.index[item] = set()
            self.index[item].add(self.numTransactions)

    def load(self, data):
        if not isinstance(data, str):
            raise TypeError("InvertedIndex.load() expects a string") 
        for transaction in data.splitlines():
            self._add([Item(s) for s in transaction.split(",")])

    def loadCSV(self, csvFilePath):
        if not isinstance(csvFilePath, str):
            raise TypeError("InvertedIndex.loadCSV() expects a path as string")
        with open(csvFilePath, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for line in reader:
                transaction = map(Item, line)
                self._add(transaction)

    def items(self):
        return self.index.keys()

    def support(self, itemset):
        for item in itemset:
            if not isinstance(item, Item):
                raise TypeError("Itemset must contain only Items")
        # print("index.Support({})".format(",".join(map(str, itemset))))
        if not isinstance(itemset, set) and not isinstance(itemset, frozenset):
            raise TypeError("InvertedIndex.support() expects a set of items") 
        return len(set.intersection(*[self.index[i] for i in itemset])) / self.numTransactions

def TestInvertedIndex():    
    data = ("a,b,c,d,e,f\n"
            "g,h,i,j,k,l\n"
            "z,x\n"
            "z,x\n"
            "z,x,y\n"
            "z,x,y,i\n")
    index = InvertedIndex();
    index.load(data);
    assert(index.support({Item("a")}) == 1 / 6);
    assert(index.support({Item("b")}) == 1 / 6);
    assert(index.support({Item("c")}) == 1 / 6);
    assert(index.support({Item("d")}) == 1 / 6);
    assert(index.support({Item("e")}) == 1 / 6);
    assert(index.support({Item("f")}) == 1 / 6);
    assert(index.support({Item("h")}) == 1 / 6);
    assert(index.support({Item("i")}) == 2 / 6);
    assert(index.support({Item("j")}) == 1 / 6);
    assert(index.support({Item("k")}) == 1 / 6);
    assert(index.support({Item("l")}) == 1 / 6);
    assert(index.support({Item("z")}) == 4 / 6);
    assert(index.support({Item("x")}) == 4 / 6);
    assert(index.support({Item("y")}) == 2 / 6);

    sup_zx = index.support({Item("z"), Item("x")});
    assert(sup_zx == 4 / 6);

    sup_zxy = index.support({Item("z"), Item("x"), Item("y")});
    assert(sup_zxy == 2 / 6);

    sup_zxyi = index.support({Item("z"), Item("x"), Item("y"), Item("i")});
    assert(sup_zxyi == 1 / 6);

if __name__ == "__main__":
    TestInvertedIndex()
