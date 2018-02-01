import numpy
from collections import Counter
from rollingmean import RollingMean
from scipy import stats

KS_TEST_CONFIDENCE = 0.05
MAX_PATTERN_SET_SIZE = 100
MAX_NUM_PATTERN_SAMPLES = 100


def outliers_iqr(ys):
    quartile_1, quartile_3 = numpy.percentile(ys, [25, 75])
    iqr = quartile_3 - quartile_1
    lower_bound = quartile_1 - (iqr * 1.5)
    upper_bound = quartile_3 + (iqr * 1.5)
    return [x for x in ys if x <= upper_bound and x >= lower_bound]


class Pattern:
    def __init__(self, id):
        self.id = id
        self.samples = []  # "Volatility Window"
        self.connections = Counter()  # Transition network.

    def ks_test(self, drift_interval):
        assert(len(self.samples) > 0)
        (_, p_value) = stats.ks_2samp(numpy.array(
            [drift_interval]), numpy.array(self.samples))
        return p_value

    def mean(self):
        rolling_mean = RollingMean()
        for sample in self.samples:
            rolling_mean.add_sample(sample)
        return rolling_mean.mean()

    def add_sample(self, drift_interval):
        self.samples.append(drift_interval)
        # Remove outliers.
        if len(self.samples) > 5:
            self.samples = outliers_iqr(self.samples)
        # Ensure patterns don't grow unbounded.
        if len(self.samples) > MAX_NUM_PATTERN_SAMPLES:
            self.samples.pop(0)


class VolatilityDetector:
    def __init__(self):
        self.last_drift_transaction_num = 0
        self.patterns = dict()
        self.next_pattern_id = 1
        self.last_drift_pattern_id = None
        self.last_drift_confidence = None

    def drift_confidence(self, transaction_num):
        if self.last_drift_pattern_id is None or len(
                self.patterns[self.last_drift_pattern_id].connections) == 0:
            return 1.0

        # From the top ten most probable transitions from previous drift,
        # find the two closest to the current transaction num. Note: the
        # closest may be behind us.
        assert(len(self.patterns[self.last_drift_pattern_id].connections) > 0)
        closest_ids = []
        top10 = list(
            self.patterns[self.last_drift_pattern_id].connections.most_common(10))
        assert(len(top10) > 0)
        for id, _ in top10:
            expected_drift_interval = self.patterns[id].mean()
            expected_drift_position = self.last_drift_transaction_num + expected_drift_interval
            distance = abs(transaction_num - expected_drift_position)
            closest_ids = sorted(
                closest_ids + [(id, distance, expected_drift_interval)], key=lambda x: x[1])[:2]

        # Find the maximum of the two closest expected drift points' probability
        # distribution function, and the maximum value of the two closest expected
        # drift points' PDF at the current transaction number.
        max_pdf = 0
        loc_max_pdf = 0
        previous_interval = 0
        assert(len(closest_ids) <= 2)
        assert(len(closest_ids) > 0)
        for _, distance, interval in closest_ids:
            x = transaction_num - self.last_drift_transaction_num
            loc = interval
            assert(previous_interval < interval)
            scale = (interval - previous_interval) / 2
            previous_interval = interval
            max_pdf = max(max_pdf, stats.norm.pdf(loc, loc, scale))
            loc_max_pdf = max(loc_max_pdf, stats.norm.pdf(x, loc, scale))

        loc_max_pdf /= max_pdf
        assert(loc_max_pdf >= 0 and loc_max_pdf <= 1)
        return loc_max_pdf

    def add(self, transaction_num):
        drift_interval = transaction_num - self.last_drift_transaction_num
        self.last_drift_transaction_num = transaction_num

        # Find the pattern which has the highest Kolmogorov-Smirnov test
        # statistic value, i.e. the most likely to be from the same
        # distribution.
        max_p_val = 0
        max_p_val_id = 0
        for id, pattern in self.patterns.items():
            p_val = pattern.ks_test(drift_interval)
            if p_val > max_p_val:
                max_p_val = p_val
                max_p_val_id = id

        if max_p_val > KS_TEST_CONFIDENCE:
            # Found at least one pattern.
            id = max_p_val_id
        else:
            # None of the KS p-values are above the threshold, so none of the
            # existing patterns are likely from the same distribution. Create a
            # new pattern.
            id = self.next_pattern_id
            self.next_pattern_id += 1
            self.patterns[id] = Pattern(id)
        self.patterns[id].add_sample(drift_interval)

        # Update transition matrix.
        if self.last_drift_pattern_id is not None:
            self.patterns[self.last_drift_pattern_id].connections[id] += 1
        self.last_drift_pattern_id = id

        self.patterns[id].last_hit_transaction_num = transaction_num

        # Ensure pattern set doesn't grow unbounded.
        if len(self.patterns) > MAX_PATTERN_SET_SIZE:
            # Find the pattern that was least recently hit.
            lru_transaction_num = transaction_num
            lru_pattern_id = id
            for pattern_id, pattern in self.patterns.items():
                if pattern.last_hit_transaction_num < lru_transaction_num:
                    lru_transaction_num = pattern.last_hit_transaction_num
                    lru_pattern_id = pattern_id
            # Remove the pattern.
            self.patterns.pop(lru_pattern_id)
            # Remove connections in the network to the pattern being removed.
            for pattern_id, pattern in self.patterns.items():
                pattern.connections.pop(lru_pattern_id)
