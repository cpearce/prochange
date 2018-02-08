import numpy
from collections import Counter
from rollingmean import RollingMean
from scipy import stats

SIMILARITY_TEST_CONFIDENCE = 0.95
MAX_PATTERN_SET_SIZE = 100
MAX_NUM_PATTERN_SAMPLES = 100

# Set to false to use ks-test instead for finding which pattern
# to add a drift interval to.
USE_CHI_SQUARED_SIMILARITY = False


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
            assert(len(self.samples) > 0)
        # Ensure patterns don't grow unbounded.
        if len(self.samples) > MAX_NUM_PATTERN_SAMPLES:
            self.samples.pop(0)

    def chisquare(self, drift_interval):
        samples = self.samples
        if len(samples) == 1:
            samples += [samples[0]]
        (_, p_val) = stats.chisquare([drift_interval], samples)
        return p_val

    def similarity(self, drift_interval):
        if USE_CHI_SQUARED_SIMILARITY:
            return self.chisquare(drift_interval)
        else:
            return self.ks_test(drift_interval)


class PatternNetwork:
    def __init__(self):
        self.last_drift_transaction_num = 0
        self.patterns = dict()
        self.next_pattern_id = 1
        self.last_drift_pattern_id = None

    def add(self, transaction_num):
        drift_interval = transaction_num - self.last_drift_transaction_num
        self.last_drift_transaction_num = transaction_num

        # Find the pattern which has the highest Kolmogorov-Smirnov test
        # statistic value, i.e. the most likely to be from the same
        # distribution.
        max_p_val = 0
        max_p_val_id = 0
        for id, pattern in self.patterns.items():
            p_val = pattern.similarity(drift_interval)
            if p_val > max_p_val:
                max_p_val = p_val
                max_p_val_id = id

        if max_p_val > SIMILARITY_TEST_CONFIDENCE:
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

    def likely_connections_at(
            self,
            sample_size,
            num_connections,
            transaction_num):
        if self.last_drift_pattern_id is None or len(
                self.patterns[self.last_drift_pattern_id].connections) == 0:
            return []
        drifts = []
        most_common = list(
            self.patterns[self.last_drift_pattern_id].connections.most_common(sample_size))
        assert(len(most_common) > 0)
        for id, _ in most_common:
            drift_interval = self.patterns[id].mean()
            drift_position = self.last_drift_transaction_num + drift_interval
            distance = abs(transaction_num - drift_position)
            drifts += [(distance, drift_position, drift_interval)]
        # Sort by distance.
        drifts.sort(key=lambda x: x[0])
        assert(len(drifts) > 0)
        return list(map(lambda x: (x[1], x[2]), drifts[:num_connections]))


class VolatilityDetector:
    def __init__(self):
        self.pattern_network = PatternNetwork()
        self.last_drift_confidence = None

    def drift_confidence(self, transaction_num):
        # Find the maximum of the two closest expected drift points' probability
        # distribution function, and the maximum value of the two closest expected
        # drift points' PDF at the current transaction number.
        connections = self.pattern_network.likely_connections_at(
            10, 2, transaction_num)
        if len(connections) == 0:
            return 1.0
        max_pdf = 0
        position_max_pdf = 0
        assert(len(connections) > 0)
        for position, interval in connections:
            scale = interval / 2
            max_pdf = max(max_pdf, stats.norm.pdf(position, position, scale))
            pdf = stats.norm.pdf(transaction_num, position, scale)
            position_max_pdf = max(position_max_pdf, pdf)

        position_max_pdf /= max_pdf
        assert(position_max_pdf >= 0 and position_max_pdf <= 1)
        return position_max_pdf

    def add(self, transaction_num):
        self.pattern_network.add(transaction_num)


class FixedConfidenceVolatilityDetector:
    # VolatilityDetector that always returns a drift confidence of a fixed value.
    # Useful for testing effectiveness of the adaptive VolatilityDetector
    # above.
    def __init__(self, confidence):
        self.confidence = confidence

    def add(self, transaction_num):
        pass

    def drift_confidence(self, transaction_num):
        return self.confidence
