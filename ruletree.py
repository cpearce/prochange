from item import Item
from collections import Counter


class RuleTreeNode:
    def __init__(self):
        self.antecedent_children = dict()
        self.consequent_children = set()

    def insert(self, antecedent, consequent):
        if len(antecedent) == 0:
            self.consequent_children.add(consequent)
            return
        item = antecedent[0]
        if item not in self.antecedent_children:
            self.antecedent_children[item] = RuleTreeNode()
        self.antecedent_children[item].insert(antecedent[1:], consequent)

    def record_matches(self, itemset, path, match_counter):
        if len(itemset) == 0:
            return False
        found_match = False
        for index in range(len(itemset)):
            item = itemset[index]
            if item in self.antecedent_children:
                found_match |= self.antecedent_children[item].record_matches(
                    itemset[index + 1:], path + [item], match_counter)
            if item in self.consequent_children:
                match_counter[(tuple(path), item)] += 1
                found_match = True
        return found_match


class RuleTree:
    def __init__(self):
        self.root = RuleTreeNode()
        self.match_counter = Counter()
        self.rag_bag_count = 0
        self.transaction_count = 0

    def insert(self, antecedent, consequent):
        if len(antecedent) == 0:
            raise TypeError("antecedent should be non-empty")
        if len(consequent) != 1:
            raise TypeError("consequent set should contain only 1 Item")
        consequent = list(consequent)[0]
        if not isinstance(consequent, Item):
            raise TypeError("consequent should be an Item")
        antecedent = list(antecedent)
        if not all(map(lambda i: isinstance(i, Item), antecedent)):
            raise TypeError("antecedent should contain Items")
        antecedent.sort()
        self.root.insert(antecedent, consequent)
        self.match_counter[(tuple(antecedent), consequent)] = 0

    def record_matches(self, itemset):
        itemset = list(itemset)
        if not all(map(lambda i: isinstance(i, Item), itemset)):
            raise TypeError("itemset should contain Items")
        itemset.sort()
        found_match = self.root.record_matches(itemset, [], self.match_counter)
        if not found_match:
            self.rag_bag_count += 1
        self.transaction_count += 1

    def rag_bag(self):
        return self.rag_bag_count / self.transaction_count

    # Returns vector of rule supports.
    def match_vector(self):
        return list(map(lambda i: i / self.transaction_count,
                        map(lambda i: i[1],
                            sorted(self.match_counter.items(),
                                   key=lambda i: i[0]))))

    def mean_rule_support(self):
        v = self.match_vector()
        assert(len(v) > 0)
        if len(v) == 0:
            return (0, 0)
        return (sum(v) / len(v), len(v))

    def clear_rule_match_counts(self):
        self.match_counter.clear()
        self.transaction_count = 0
        self.rag_bag_count = 0

    def take_and_add_matches(self, other):
        self.match_counter.update(other.match_counter)
        self.transaction_count += other.transaction_count
        self.rag_bag_count += other.rag_bag_count
        other.clear_rule_match_counts()

    def take_and_overwrite_matches(self, other):
        self.clear_rule_match_counts()
        self.take_and_add_matches(other)
