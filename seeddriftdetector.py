from copy import deepcopy
from driftdetector import SAMPLE_INTERVAL
from driftdetector import Drift
from hoeffdingbound import hoeffding_bound
from rollingmean import RollingMean
from ruletree import RuleTree
from driftdetector import ProSeedDriftAlgorithm
from driftdetector import SeedDriftAlgorithm


BlockCompareConfidence = 0.1
TrainingCompareConfidence = 0.05

# If we're within this many transactions of the next expected drift
# point, ProSeed won't merge blocks, it will drop them.
ProSeedMergeExclusionZone = 1000


class SeedDriftDetector:
    def __init__(self, volatility_detector=None):
        self.volatility_detector = volatility_detector

    def make_test_tree(self):
        # Copy the training rule tree, so that we get a copy of the rules.
        tree = deepcopy(self.training_rule_tree)
        # Clear the rule match counts so that we can re-generate them
        # as we read in more data.
        tree.clear_rule_match_counts()
        return tree

    def train(self, window, rules):
        self.training_rule_tree = RuleTree()
        for (antecedent, consequent, _, _, _) in rules:
            self.training_rule_tree.insert(antecedent, consequent)

        # Populate the training rule tree with the rule frequencies from
        # the training window.
        for transaction in window:
            self.training_rule_tree.record_matches(transaction)

        self.previous_rule_tree = self.make_test_tree()
        self.current_rule_tree = self.make_test_tree()

        # Record the match vector; the vector of rules' supports in the
        # training window.
        self.training_mean, self.training_len = self.training_rule_tree.rule_miss_rate()

        self.num_test_transactions = 0

    def should_merge(self, transaction_num):
        if self.volatility_detector is not None:
            # ProSeed; we'll not merge blocks within the "exclusion zone"
            # around the next expected drift point; we'll drop them instead.
            next_drift = self.volatility_detector.next_expected_drift(
                transaction_num)
            if (next_drift is not None and abs(next_drift - \
                transaction_num) < ProSeedMergeExclusionZone):
                return False
        prev_mean, prev_len = self.previous_rule_tree.rule_miss_rate()
        curr_mean, curr_len = self.current_rule_tree.rule_miss_rate()
        return hoeffding_bound(
            prev_mean,
            prev_len,
            curr_mean,
            curr_len,
            BlockCompareConfidence)

    def check_for_drift(self, transaction, transaction_num):
        # Append to current block.
        self.current_rule_tree.record_matches(transaction)

        self.num_test_transactions += 1
        if self.num_test_transactions < SAMPLE_INTERVAL:
            return None
        # Test for drift.
        self.num_test_transactions = 0

        if self.previous_rule_tree.transaction_count == 0:
            # First block, can't merge/drop.
            self.previous_rule_tree.take_and_add_matches(
                self.current_rule_tree)
            return None
        else:
            # Can the current block be merged with the previous block,
            # or should the previous be dropped?
            if self.should_merge(transaction_num):
                # Blocks are similar. Merge them.
                self.previous_rule_tree.take_and_add_matches(
                    self.current_rule_tree)
            else:
                # Otherwise the blocks are different, we'll discard data in
                # the former block.
                self.previous_rule_tree.take_and_overwrite_matches(
                    self.current_rule_tree)

        # Test to see whether training block is similar to test block.
        prev_mean, prev_len = self.previous_rule_tree.rule_miss_rate()
        if not hoeffding_bound(
                self.training_mean,
                self.training_len,
                prev_mean,
                prev_len,
                TrainingCompareConfidence):
            return Drift(drift_type=SeedDriftAlgorithm)

        return None
