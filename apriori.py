from index import InvertedIndex
from itertools import product
from item import Item
from item import ItemSet
import sys

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")


def containsAllSubsets(candidate, candidates):
    for item in candidate:
        if candidate - {item} not in candidates:
            return False
    return True


def Apriori(index, minsup):
    print("Apriori with minsup={}".format(minsup))
    candidates = set(
        [frozenset({i}) for i in index.items() if index.support({i}) >= minsup])
    results = list(candidates)
    itemsetSize = 1
    while len(candidates) > 0:
        generation = set()
        for (a, b) in product(candidates, repeat=2):
            if (len(a - b) == 1
                and index.support(a | b) >= minsup
                    and containsAllSubsets(a | b, candidates)):
                generation.add(frozenset(a | b))
        print(
            "Generated {} itemsets of size {}".format(
                len(generation),
                itemsetSize))
        itemsetSize += 1
        results.extend(list(generation))
        candidates = generation
    return results

