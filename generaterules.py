from item import ItemSet
from index import InvertedIndex
from apriori import apriori
from itertools import combinations
import sys


if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")


# Return a generator of (antecedent, consequent, confidence, lift, support),
# for all rules that can be generated from set of item sets.
def generate_rules(set_of_item_sets, inverted_index):
    for item_set in set_of_item_sets:
        if len(item_set) < 2:
            continue
        support = inverted_index.support(item_set)
        for antecedent in (
            frozenset(x) for x in combinations(
                item_set,
                len(item_set) - 1)):
            consequent = item_set - antecedent
            assert(len(antecedent) > 0)
            assert(len(consequent) > 0)
            confidence = support / inverted_index.support(antecedent)
            lift = confidence / inverted_index.support(consequent)
            yield (antecedent, consequent, confidence, lift, support)
