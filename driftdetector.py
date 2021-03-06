import numpy
from copy import deepcopy
from hoeffdingbound import hoeffding_bound
from rollingmean import RollingMean
from ruletree import RuleTree
from scipy.linalg import norm


VRChangeDriftAlgorithm = "vrchange"
ProChangeDriftAlgorithm = "prochange"
SeedDriftAlgorithm = "seed"
ProSeedDriftAlgorithm = "proseed"

# Number of transations which we read before collecting another
# distance sample.
SAMPLE_INTERVAL = 32

# Number of samples of the Hellinger distance of the
# rag-bag/rule-match-vector means we collect before we test against
# the training set.
SAMPLE_THRESHOLD = 30

_SQRT2 = numpy.sqrt(2)


def hellinger(p, q):
    return norm(numpy.sqrt(p) - numpy.sqrt(q)) / _SQRT2


class Drift:
    def __init__(
            self,
            drift_type,
            hellinger_value=None,
            confidence=None,
            mean=None):
        self.drift_type = drift_type
        self.hellinger_value = hellinger_value
        self.confidence = confidence
        self.mean = mean


class DriftDetector:
    def __init__(self, volatility_detector):
        self.volatility_detector = volatility_detector

    def train(self, window, rules):
        assert(len(rules) > 0)
        assert(len(window) > 0)
        self.training_rule_tree = RuleTree(len(window))
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

    def check_for_drift(self, transaction, transaction_num):
        self.test_rule_tree.record_matches(transaction)
        self.num_test_transactions += 1
        if self.num_test_transactions < SAMPLE_INTERVAL:
            return None

        # Sample and test for drift.
        self.num_test_transactions = 0

        if (self.rule_vec_mean.n + 1 > SAMPLE_THRESHOLD or
                self.rag_bag_mean.n + 1 > SAMPLE_THRESHOLD):
            # We'll need the drift confidence below. Calculate it.
            # Note: the +1 is there because of the add_sample() call below.
            gamma = self.volatility_detector.drift_confidence(
                transaction_num)
            print(
                "gamma at transaction {} is {}".format(
                    transaction_num, gamma))
            drift_confidence = 2.5 - gamma

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
        if not hoeffding_bound(self.training_rule_tree.rag_bag(),
                               self.training_rule_tree.transaction_count,
                               self.test_rule_tree.rag_bag(),
                               self.test_rule_tree.transaction_count,
                               0.05):
            return Drift(drift_type="rag-bag")

        return None
