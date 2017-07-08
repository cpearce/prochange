from index import InvertedIndex
from apriori import apriori
from item import Item, ItemSet
from generaterules import generate_rules
import sys

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")


def test_apriori():
    data = ("a,b,c,d,e,f\n"
            "g,h,i,j,k,l\n"
            "z,x\n"
            "z,x\n"
            "z,x,y\n"
            "z,x,y,i\n")

    expectedItemSets = {ItemSet("i"): 2 / 6,
                        ItemSet("z"): 4 / 6,
                        ItemSet("x"): 4 / 6,
                        ItemSet("y"): 2 / 6,
                        ItemSet("xz"): 4 / 6,
                        ItemSet("yz"): 2 / 6,
                        ItemSet("xy"): 2 / 6,
                        ItemSet("xyz"): 2 / 6}

    index = InvertedIndex()
    index.load(data)
    itemsets = apriori(index, 2 / 6)
    assert(set(expectedItemSets.keys()) == set(itemsets))
    for itemset in itemsets:
        assert(expectedItemSets[itemset] == index.support(itemset))

    print("Itemsets={}".format([i for i in itemsets if len(i) > 1]))

    # (antecedent, consequent, confidence, lift, support)
    expectedRules = {
        (frozenset({Item("x"), Item("y")}), frozenset({Item("z")}), 1, 1.5, 1/3),
        (frozenset({Item("x")}), frozenset({Item("y")}), 0.5, 1.5, 1/3),
        (frozenset({Item("x")}), frozenset({Item("z"), Item("y")}), 0.5, 1.5, 1/3),
        (frozenset({Item("x")}), frozenset({Item("z")}), 1, 1.5, 2/3),
        (frozenset({Item("y")}), frozenset({Item("x")}), 1, 1.5, 1/3),
        (frozenset({Item("y")}), frozenset({Item("z"), Item("x")}), 1, 1.5, 1/3),
        (frozenset({Item("y")}), frozenset({Item("z")}), 1, 1.5, 1/3),
        (frozenset({Item("z"), Item("x")}), frozenset({Item("y")}), 0.5, 1.5, 1/3),
        (frozenset({Item("z"), Item("y")}), frozenset({Item("x")}), 1, 1.5, 1/3),
        (frozenset({Item("z")}), frozenset({Item("x"), Item("y")}), 0.5, 1.5, 1/3),
        (frozenset({Item("z")}), frozenset({Item("x")}), 1, 1.5, 2/3),
        (frozenset({Item("z")}), frozenset({Item("y")}), 0.5, 1.5, 1/3),
    }

    rules = set(generate_rules(itemsets, 0, 0, index))

    for (antecedent,
         consequent,
         confidence,
         lift,
         support) in rules:
        print("{}, {} conf={:.4f}, {:.4f}, {:.4f}".
              format(antecedent, consequent, confidence, lift, support))

    assert(rules == expectedRules)
