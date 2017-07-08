from item import ItemSet
from index import InvertedIndex
from apriori import apriori
from itertools import chain, combinations
import sys


if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")


# Modified version of itertools powerset recipie; this version outputs all
# subsets of size >= 1 and size <= len(iterable)-1. The later condition
# ensures that we can subtract the sets in the powerset from the itemset
# and have a non-empty remainder to act as the consequent in generate_rules
# below.
def powerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(1, len(s)))

# Return a generator of (antecedent, consequent, confidence, lift, support),
# for all rules that can be generated from set of item sets.
def generate_rules(set_of_item_sets, min_confidence, min_lift, inverted_index):
    for item_set in set_of_item_sets:
        if len(item_set) < 2:
            continue
        support = inverted_index.support(item_set)
        for antecedent in (frozenset(x) for x in powerset(item_set)):
            consequent = item_set - antecedent
            assert(len(antecedent) > 0)
            assert(len(consequent) > 0)
            confidence = support / inverted_index.support(antecedent)
            if confidence < min_confidence:
                continue
            lift = confidence / inverted_index.support(consequent)
            if lift < min_lift:
                continue
            yield (antecedent, consequent, confidence, lift, support)
