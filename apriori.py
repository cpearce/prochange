from index import InvertedIndex
from itertools import product

testDataSet = ("a,b,c,d,e,f\n"
               "g,h,i,j,k,l\n"
               "z,x\n"
               "z,x\n"
               "z,x,y\n"
               "z,x,y,i\n")

def containsAllSubsets(candidate, candidates):
    for item in candidate:
        if candidate - {item} not in candidates:
            return False
    return True

def Apriori(index, minsup):
    candidates = set([frozenset(i) for i in index.items() if index.support({i}) >= minsup])
    results = list(candidates)
    while len(candidates) > 0:
        generation = set()
        for (a,b) in product(candidates, repeat=2):
            if (len(a - b) == 1 and
                index.support(a | b) >= minsup and
                containsAllSubsets(a | b, candidates)):
                generation.add(frozenset(a | b))
        results.extend(list(generation))
        candidates = generation
    return results

testDataSetItemSets = { frozenset({"i"}) : 2/6,
                        frozenset({"z"}) : 4/6,
                        frozenset({"x"}) : 4/6,
                        frozenset({"y"}) : 2/6,
                        frozenset({"x","z"}) : 4/6,
                        frozenset({"y","z"}) : 2/6,
                        frozenset({"x","y"}) : 2/6,
                        frozenset({"x","y","z"}) : 2/6}

def TestApriori():
    index = InvertedIndex();
    index.load(testDataSet);
    itemsets = Apriori(index, 2/6)
    assert(set(testDataSetItemSets.keys()) == set(itemsets))
    for itemset in itemsets:
        assert(testDataSetItemSets[itemset] == index.support(itemset))

if __name__ == "__main__":
    TestApriori();
