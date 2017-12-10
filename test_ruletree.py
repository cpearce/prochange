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

    tree = RuleTree()
    for (antecedent, consequent) in rules:
        tree.insert(antecedent, consequent)

    # (ItemSet, [(antecedent, consquent)...])
    test_cases = [
        ("abcd", [1, 0, 0, 1, 0]),
        ("geabcd", [1, 0, 0.5, 1, 0.5])
    ]
    test_cases = list(map(lambda t: (ItemSet(t[0]), t[1]), test_cases))
    for (itemset, expected_results) in test_cases:
        tree.record_matches(itemset)
        assert(expected_results == tree.match_vector())
