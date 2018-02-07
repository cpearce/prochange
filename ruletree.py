from item import Item
from collections import Counter
from collections import deque


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

    def is_empty(self):
        return len(
            self.antecedent_children) == 0 and len(
            self.consequent_children) == 0

    def matches(self, itemset, path):
        if len(itemset) == 0:
            return
        for index in range(len(itemset)):
            item = itemset[index]
            if item in self.antecedent_children:
                for match in self.antecedent_children[item].matches(
                        itemset[index + 1:], path + [item]):
                    yield match
            if item in self.consequent_children:
                yield (tuple(path), item)

    def rules(self, antecedent_path):
        result = set()
        for consequent in self.consequent_children:
            result.add((tuple(antecedent_path), consequent))
        for antecedent, child in self.antecedent_children.items():
            result |= child.rules(antecedent_path + [antecedent])
        return result


class RuleTree:
    def __init__(self, window_size=None):
        self.root = RuleTreeNode()
        self.match_counter = Counter()
        self.rag_bag_count = 0
        self.transaction_count = 0
        self.window_size = window_size
        self.window = deque()

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
        found_match = False
        for (antecedent, consequent) in self.root.matches(itemset, []):
            self.match_counter[antecedent, consequent] += 1
            found_match = True
        if not found_match:
            self.rag_bag_count += 1
        self.transaction_count += 1
        if self.window_size is not None:
            self.window.append(itemset)
            if len(self.window) > self.window_size:
                itemset = self.window.popleft()
                self.remove_matches(itemset)
            assert(self.transaction_count == len(self.window))

    def remove_matches(self, itemset):
        if not all(map(lambda i: isinstance(i, Item), itemset)):
            raise TypeError("itemset should contain Items")
        found_match = False
        for (antecedent, consequent) in self.root.matches(itemset, []):
            self.match_counter[(antecedent, consequent)] -= 1
            found_match = True
        if not found_match:
            self.rag_bag_count -= 1
        self.transaction_count -= 1

    def rag_bag(self):
        return self.rag_bag_count / self.transaction_count

    # Returns vector of rule supports.
    def match_vector(self):
        return list(map(lambda i: i / self.transaction_count,
                        map(lambda i: i[1],
                            sorted(self.match_counter.items(),
                                   key=lambda i: i[0]))))

    def rule_miss_rate(self):
        # Can only take match counts if we're not using a sliding window.
        assert(self.window_size is None)
        return ((self.transaction_count - self.rag_bag_count) /
                self.transaction_count, self.transaction_count)

    def clear_rule_match_counts(self):
        # Can only take match counts if we're not using a sliding window.
        assert(self.window_size is None)
        self.match_counter.clear()
        self.transaction_count = 0
        self.rag_bag_count = 0

    def take_and_add_matches(self, other):
        # Can only take match counts if we're not using a sliding window.
        assert(self.window_size is None)
        self.match_counter.update(other.match_counter)
        self.transaction_count += other.transaction_count
        self.rag_bag_count += other.rag_bag_count
        other.clear_rule_match_counts()

    def take_and_overwrite_matches(self, other):
        # Can only take match counts if we're not using a sliding window.
        assert(self.window_size is None)
        self.clear_rule_match_counts()
        self.take_and_add_matches(other)

    def match_count_of(self, antecedent, consequent):
        if not isinstance(antecedent, tuple):
            raise TypeError("antecedent should be a Tuple of Items")
        if not isinstance(consequent, Item):
            raise TypeError("consequent should be an Item")
        return self.match_counter[(antecedent, consequent)]

    def rules(self):
        # Returns a set of (antecedent,consequent) pairs of rules in the tree.
        return self.root.rules([])
