from item import ItemSet
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
    return chain.from_iterable(
        combinations(
            s, r) for r in range(
            1, len(s) + 1))

# Return the set of (antecedent, consequent, confidence, lift, support),
# for all rules that can be generated from set of item sets.


def generate_rules(
        itemsets,
        itemset_counts,
        num_transactions,
        min_confidence,
        min_lift):
    if not isinstance(itemset_counts, dict):
        raise TypeError("argument itemset_counts must be dict")
    result = set()

    def calculate_support(i):
        return itemset_counts[i] / num_transactions

    for itemset in itemsets:
        if len(itemset) < 2:
            continue
        for item in itemset:
            consequent = frozenset([item])
            for antecedent in (frozenset(x)
                               for x in powerset(itemset - consequent)):
                assert(len(antecedent) > 0)
                assert(len(consequent) == 1)
                support = calculate_support(antecedent | consequent)
                confidence = support / calculate_support(antecedent)
                if confidence < min_confidence:
                    continue
                lift = confidence / calculate_support(consequent)
                if lift < min_lift:
                    continue
                result.add((antecedent, consequent, confidence, lift, support))
    return result
