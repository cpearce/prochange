# Example usage:
#   $ python3 virtual-change-dectection.py \
#       --input datasets/poker-hand-training-true.data \
#       --output poker.rules \
#       --min-confidence 0.05 \
#       --min-support 0.05 \
#       --min-lift 1.0 \
#       --training-window-size 2500 \
#       --drift-algorithm seed

import sys
import time
from argparse import ArgumentParser
from argparse import ArgumentTypeError
from fptree import mine_fp_tree
from generaterules import generate_rules
from datasetreader import DatasetReader
from itertools import islice
from driftdetector import DriftDetector
from driftdetector import SeedDriftAlgorithm
from driftdetector import ProSeedDriftAlgorithm
from driftdetector import VirtualDriftAlgorithm
from seeddriftdetector import SeedDriftDetector
from volatilitydetector import ProSeedVolatilityDetector
from volatilitydetector import VolatilityDetector
from volatilitydetector import FixedConfidenceVolatilityDetector


def set_to_string(s):
    ss = ""
    for x in sorted(s):
        if ss != "":
            ss += " "
        ss += str(x)
    return ss


def float_between_0_and_1(string):
    value = float(string)
    if value < 0.0 or value > 1.0:
        msg = "%r is not in range [0,1]" % string
        raise ArgumentTypeError(msg)
    return value


def float_gteq_1(string):
    value = float(string)
    if value < 1.0:
        msg = "%r is not in range [1,∞]" % string
        raise ArgumentTypeError(msg)
    return value


def valid_drift_algorithm(value):
    valid_modes = [
        VirtualDriftAlgorithm,
        SeedDriftAlgorithm,
        ProSeedDriftAlgorithm]
    if value not in valid_modes:
        msg = "{} is not in valid modes {}".format(value, valid_modes)
        raise ArgumentTypeError(msg)
    return value


def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))


def parse_args():
    parser = ArgumentParser(
        description="Association rule data mining in Python - Virtual change detection")
    parser.add_argument("--input", dest="input", required=True)
    parser.add_argument("--output", dest="output", required=True)
    parser.add_argument(
        "--drift-algorithm",
        dest="drift_algorithm",
        type=valid_drift_algorithm,
        required=False,
        default=VirtualDriftAlgorithm)
    parser.add_argument(
        "--training-window-size",
        dest="training_window_size",
        type=int,
        required=True,
        action="store")
    parser.add_argument(
        "--min-confidence",
        dest="min_confidence",
        type=float_between_0_and_1,
        required=True)
    parser.add_argument(
        "--min-support",
        dest="min_support",
        type=float_between_0_and_1,
        required=True)
    parser.add_argument(
        "--min-lift",
        dest="min_lift",
        type=float_gteq_1,
        required=True)
    parser.add_argument(
        "--generate-maximal-itemsets",
        dest="maximal_itemsets",
        action='store_true')
    parser.add_argument(
        "--fixed-drift-confidence",
        dest="fixed_drift_confidence",
        type=float_between_0_and_1,
        required=False,
        default=None)
    return parser.parse_args()


def write_rules_to_file(rules, output_filename):
    with open(output_filename, "w") as output_file:
        output_file.write("Antecedent->Consequent,Confidence,Lift,Support\n")
        for (antecedent,
             consequent,
             confidence,
             lift,
             support) in rules:
            output_file.write(
                "{} -> {},{:.4f},{:.4f},{:.4f}\n". format(
                    set_to_string(antecedent),
                    set_to_string(consequent),
                    confidence,
                    lift,
                    support))


def make_volatility_detector(args):
    if args.drift_algorithm == VirtualDriftAlgorithm:
        if args.fixed_drift_confidence is not None:
            return FixedConfidenceVolatilityDetector(
                args.fixed_drift_confidence)
        else:
            return VolatilityDetector()

    # Seed and ProSeed can't use a fixed confidence.
    assert(args.fixed_drift_confidence is None)

    if args.drift_algorithm == ProSeedDriftAlgorithm:
        return ProSeedVolatilityDetector()

    return None


def make_drift_detector(args, volatility_detector):
    if args.drift_algorithm == VirtualDriftAlgorithm:
        return DriftDetector(volatility_detector)
    if args.drift_algorithm in [SeedDriftAlgorithm, ProSeedDriftAlgorithm]:
        return SeedDriftDetector(args.drift_algorithm, volatility_detector)
    return None


def main():
    args = parse_args()
    program_start = time.time()

    print("ARMPY - Association Rule Mining using Python.")
    print("Change detection.")
    print("Drift Algorithm: {}".format(args.drift_algorithm))
    print("Input file: {}".format(args.input))
    print("Output file prefix: {}".format(args.output))
    print("Training window size: {}".format(args.training_window_size))
    print("Minimum confidence: {}".format(args.min_confidence))
    print("Minimum support: {}".format(args.min_support))
    print("Minimum lift: {}".format(args.min_lift))
    if args.fixed_drift_confidence is not None:
        print(
            "Fixed drift confidence of: {}".format(
                args.fixed_drift_confidence))

    print("Generating maximal itemsets: {}".format(args.maximal_itemsets))

    print("Generating frequent itemsets using FPGrowth...", flush=True)
    reader = iter(DatasetReader(args.input))
    transaction_num = 0
    end_of_last_window = 0
    cohort_num = 1
    volatility_detector = make_volatility_detector(args)
    while True:
        window = take(args.training_window_size, reader)
        if len(window) == 0:
            print("End of stream")
            break
        print("")
        print(
            "Mining window [{},{}]".format(
                transaction_num,
                transaction_num + len(window)))
        end_of_last_window = transaction_num + len(window)
        transaction_num += len(window)
        print("Running FP-Growth...", flush=True)
        start = time.time()

        (itemsets, itemset_counts, num_transactions) = mine_fp_tree(
            window, args.min_support, args.maximal_itemsets)
        assert(num_transactions == len(window))

        duration = time.time() - start
        print(
            "FPGrowth mined {} items in {:.2f} seconds".format(
                len(itemsets),
                duration))

        print("Generating rules...", flush=True)
        start = time.time()
        rules = list(
            generate_rules(
                itemsets,
                itemset_counts,
                num_transactions,
                args.min_confidence,
                args.min_lift))
        duration = time.time() - start
        print(
            "Generated {} rules in {:.2f} seconds".format(
                len(rules),
                duration),
            flush=True)

        start = time.time()
        output_filename = args.output + "." + str(cohort_num)
        cohort_num += 1
        write_rules_to_file(rules, output_filename)
        print(
            "Wrote rules for cohort {} to file {} in {:.2f} seconds".format(
                cohort_num, output_filename, duration),
            flush=True)

        drift_detector = make_drift_detector(args, volatility_detector)
        drift_detector.train(window, rules)

        # Read transactions until a drift is detected.
        for transaction in reader:
            transaction_num += 1
            drift = drift_detector.check_for_drift(
                transaction, transaction_num)
            if drift is not None:
                print(
                    "Detected drift of type {} at transaction {}, {} after end of training window".format(
                        drift.drift_type,
                        transaction_num,
                        transaction_num -
                        end_of_last_window))
                if drift.hellinger_value is not None:
                    print(
                        "Hellinger value: {}, confidence interval: {} ± {} ([{},{}])".format(
                            drift.hellinger_value,
                            drift.mean,
                            drift.confidence,
                            drift.mean - drift.confidence,
                            drift.mean + drift.confidence))
                # Record the drift in the volatility detector. This is used inside
                # the drift detector to help determine how large a confidence interval
                # is required when detecting drifts.
                if not volatility_detector is None:
                    volatility_detector.add(transaction_num)
                # Break out of the inner loop, we'll jump back up to the top and mine
                # a new training window.
                break

        if len(window) < args.training_window_size:
            print("End of stream")
            break

    duration = time.time() - program_start
    print("Total runtime {:.2f} seconds".format(duration))

    return 0


if __name__ == "__main__":
    sys.exit(main())
