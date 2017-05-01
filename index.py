import csv

class InvertedIndex:
    def __init__(self):
        self.index = dict()
        self.numTransactions = 0

    def _add(self, transaction):
        self.numTransactions += 1
        for item in transaction:
            if item not in self.index:
                self.index[item] = set()
            self.index[item].add(self.numTransactions)

    def load(self, data):
        if not isinstance(data, str):
            raise TypeError("InvertedIndex.load() expects a string") 
        for transaction in data.splitlines():
            self._add([s.strip() for s in transaction.split(",")])

    def loadCSV(self, csvFilePath):
        if not isinstance(data, str):
            raise TypeError("InvertedIndex.loadCSV() expects a path as string")
        with open(csvFilePath, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for transaction in reader:
                self._add(transaction)

    def items(self):
        return self.index.keys()

    def support(self, itemset):
        if not isinstance(itemset, set) and not isinstance(itemset, frozenset):
            raise TypeError("InvertedIndex.support() expects a set of items") 
        return len(set.intersection(*[self.index[i] for i in itemset])) / self.numTransactions

testDataSet = ("a,b,c,d,e,f\n"
               "g,h,i,j,k,l\n"
               "z,x\n"
               "z,x\n"
               "z,x,y\n"
               "z,x,y,i\n")

def TestInvertedIndex():    
    # Test: Dataset 1, check loading, test supports.
    index = InvertedIndex();
    index.load(testDataSet);
    assert(index.support({"a"}) == 1 / 6);
    assert(index.support({"b"}) == 1 / 6);
    assert(index.support({"c"}) == 1 / 6);
    assert(index.support({"d"}) == 1 / 6);
    assert(index.support({"e"}) == 1 / 6);
    assert(index.support({"f"}) == 1 / 6);
    assert(index.support({"h"}) == 1 / 6);
    assert(index.support({"i"}) == 2 / 6);
    assert(index.support({"j"}) == 1 / 6);
    assert(index.support({"k"}) == 1 / 6);
    assert(index.support({"l"}) == 1 / 6);
    assert(index.support({"z"}) == 4 / 6);
    assert(index.support({"x"}) == 4 / 6);
    assert(index.support({"y"}) == 2 / 6);

    sup_zx = index.support({"z", "x"});
    assert(sup_zx == 4 / 6);

    sup_zxy = index.support({"z", "x", "y"});
    assert(sup_zxy == 2 / 6);

    sup_zxyi = index.support({"z", "x", "y", "i"});
    assert(sup_zxyi == 1 / 6);

if __name__ == "__main__":
    TestInvertedIndex()
