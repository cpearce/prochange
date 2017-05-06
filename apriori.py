from index import InvertedIndex
from itertools import product
from item import Item

def containsAllSubsets(candidate, candidates):
    for item in candidate:
        if candidate - {item} not in candidates:
            return False
    return True

def Apriori(index, minsup):
    print("Apriori with minsup={}".format(minsup))
    candidates = set([frozenset({i}) for i in index.items() if index.support({i}) >= minsup])
    results = list(candidates)
    itemsetSize = 1
    while len(candidates) > 0:
        generation = set()
        for (a,b) in product(candidates, repeat=2):
            if (len(a - b) == 1
                and index.support(a | b) >= minsup
                and containsAllSubsets(a | b, candidates)):
                generation.add(frozenset(a | b))
        print("Generated {} itemsets of size {}".format(len(generation), itemsetSize))
        itemsetSize += 1
        results.extend(list(generation))
        candidates = generation
    return results

def TestApriori():
    data = ("a,b,c,d,e,f\n"
            "g,h,i,j,k,l\n"
            "z,x\n"
            "z,x\n"
            "z,x,y\n"
            "z,x,y,i\n")

    expectedItemSets = { frozenset({Item("i")}) : 2/6,
                         frozenset({Item("z")}) : 4/6,
                         frozenset({Item("x")}) : 4/6,
                         frozenset({Item("y")}) : 2/6,
                         frozenset({Item("x"),Item("z")}) : 4/6,
                         frozenset({Item("y"),Item("z")}) : 2/6,
                         frozenset({Item("x"),Item("y")}) : 2/6,
                         frozenset({Item("x"),Item("y"),Item("z")}) : 2/6}

    index = InvertedIndex();
    index.load(data);
    itemsets = Apriori(index, 2/6)
    assert(set(expectedItemSets.keys()) == set(itemsets))
    for itemset in itemsets:
        assert(expectedItemSets[itemset] == index.support(itemset))

if __name__ == "__main__":
    TestApriori();
