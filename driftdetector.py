import numpy
from copy import deepcopy
from rollingmean import RollingMean
from ruletree import RuleTree
from scipy.linalg import norm


# Number of transations which we read before collecting another
# distance sample.
SAMPLE_INTERVAL = 10

# Number of samples of the Hellinger distance of the
# rag-bag/rule-match-vector means we collect before we test against
# the training set.
SAMPLE_THRESHOLD = 30

_SQRT2 = numpy.sqrt(2)


def hellinger(p, q):
    return norm(numpy.sqrt(p) - numpy.sqrt(q)) / _SQRT2


class Drift:
    def __init__(self, drift_type, hellinger_value, confidence, mean):
        self.drift_type = drift_type
        self.hellinger_value = hellinger_value
        self.confidence = confidence
        self.mean = mean


class DriftDetector:
    def train(self, window, rules):
        self.training_rule_tree = RuleTree()
        for (antecedent, consequent, _, _, _) in rules:
            self.training_rule_tree.insert(antecedent, consequent)

        # Populate the training rule tree with the rule frequencies from
        # the training window.
        for transaction in window:
            self.training_rule_tree.record_matches(transaction)

        # Populate the test rule tree with a deep copy of the training set.
        self.test_rule_tree = deepcopy(self.training_rule_tree)

        # Record the match vector; the vector of rules' supports in the
        # training window.
        self.training_match_vec = self.training_rule_tree.match_vector()

        self.num_test_transactions = 0
        self.rule_vec_mean = RollingMean()
        self.rag_bag_mean = RollingMean()

    def check_for_drift(self, transaction, drift_confidence):
        self.test_rule_tree.record_matches(transaction)
        self.num_test_transactions += 1
        if self.num_test_transactions < SAMPLE_INTERVAL:
            return None

        # Sample and test for drift.
        self.num_test_transactions = 0

        # Detect whether the rules' supports in the test window differ
        # from the rules' supports in the training window.
        distance = hellinger(
            self.training_match_vec,
            self.test_rule_tree.match_vector())
        self.rule_vec_mean.add_sample(distance)
        if self.rule_vec_mean.n > SAMPLE_THRESHOLD:
            conf = self.rule_vec_mean.std_dev() * drift_confidence
            mean = self.rule_vec_mean.mean()
            if distance > mean + conf or distance < mean - conf:
                return Drift("rule-match-vector", distance, conf, mean)

        # Detect whether the rag bag differs between the training and
        # test windows.
        rag_bag = hellinger([self.training_rule_tree.rag_bag()], [
                            self.test_rule_tree.rag_bag()])
        self.rag_bag_mean.add_sample(rag_bag)
        if self.rag_bag_mean.n > SAMPLE_THRESHOLD:
            conf = self.rag_bag_mean.std_dev() * drift_confidence
            mean = self.rag_bag_mean.mean()
            if rag_bag > mean + conf or rag_bag < mean - conf:
                return Drift("rag-bag", rag_bag, conf, mean)

        return None
