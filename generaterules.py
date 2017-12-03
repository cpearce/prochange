from item import ItemSet
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
def generate_rules(itemsets_with_support, min_confidence, min_lift):
    for (itemset, support) in itemsets_with_support.items():
        if len(itemset) < 2:
            continue
        for antecedent in (frozenset(x) for x in powerset(itemset)):
            consequent = itemset - antecedent
            assert(len(antecedent) > 0)
            assert(len(consequent) > 0)
            confidence = support / itemsets_with_support[antecedent]
            if confidence < min_confidence:
                continue
            lift = confidence / itemsets_with_support[consequent]
            if lift < min_lift:
                continue
            yield (antecedent, consequent, confidence, lift, support)
