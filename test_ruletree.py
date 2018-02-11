from ruletree import RuleTree
from item import Item, ItemSet


def ItemList(s):
    return list(map(Item, s))


def test_basic_rule_tree():
    rules = [
        ("abc", "d"),
        ("abc", "f"),
        ("ac", "g"),
        ("bc", "d"),
        ("de", "g"),
    ]
    rules = map(lambda r: (ItemSet(r[0]), ItemSet(r[1])), rules)

    tree = RuleTree(4)
    for (antecedent, consequent) in rules:
        tree.insert(antecedent, consequent)

    # (ItemSet, [(antecedent, consquent)...])
    test_cases = [
        ("abcd", [1, 0, 0, 1, 0]),
        ("geabcd", [1, 0, 0.5, 1, 0.5]),
        ("abc", [2 / 3, 0.0, 1 / 3, 2 / 3, 1 / 3]),
        ("bcd", [0.5, 0.0, 0.25, 0.75, 0.25]),
        ("def", [0.25, 0.0, 0.25, 0.5, 0.25]),
        ("geab", [0.0, 0.0, 0.0, 0.25, 0.0]),
    ]
    test_cases = list(map(lambda t: (ItemSet(t[0]), t[1]), test_cases))
    print()
    for (itemset, expected_results) in test_cases:
        print("Adding {}".format(itemset))
        tree.record_matches(itemset)
        for (a, c) in tree.rules():
            print("  {} -> {} ; {}".format(a, c, tree.match_count_of(a, c)))
        assert(expected_results == tree.match_vector())
