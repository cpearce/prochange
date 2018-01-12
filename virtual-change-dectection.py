# Example usage:
#   $ python3 virtual-change-dectection.py \
#       --input datasets/poker-hand-training-true.data \
#       --output poker.rules \
#       --min-confidence 0.05 \
#       --min-support 0.05 \
#       --min-lift 1.0 \
#       --training-window-size 2500 \
#       --drift-confidence 1.5

import sys
import time
import numpy
from scipy.linalg import norm
from argparse import ArgumentParser
from argparse import ArgumentTypeError
from fptree import mine_fp_tree
from generaterules import generate_rules
from datasetreader import DatasetReader
from itertools import islice
from ruletree import RuleTree
from rollingmean import RollingMean
from copy import deepcopy


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


def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))


_SQRT2 = numpy.sqrt(2)


def hellinger(p, q):
    return norm(numpy.sqrt(p) - numpy.sqrt(q)) / _SQRT2


def parse_args():
    parser = ArgumentParser(
        description="Association rule data mining in Python - Virtual change detection")
    parser.add_argument("--input", dest="input", required=True)
    parser.add_argument("--output", dest="output", required=True)
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
        action='store_true'
    )
    parser.add_argument(
        "--drift-confidence",
        dest="drift_confidence",
        type=float,
        required=True)
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


def main():
    args = parse_args()
    program_start = time.time()

    print("ARMPY - Association Rule Mining using Python.")
    print("Virtual change detection.")
    print("Input file: {}".format(args.input))
    print("Output file prefix: {}".format(args.output))
    print("Training window size: {}".format(args.training_window_size))
    print("Minimum support: {}".format(args.min_confidence))
    print("Minimum confidence: {}".format(args.min_support))
    print("Minimum lift: {}".format(args.min_lift))
    print("Generating maximal itemsets: {}".format(args.maximal_itemsets))

    print("Generating frequent itemsets using FPGrowth...", flush=True)
    reader = iter(DatasetReader(args.input))
    transaction_num = 0
    end_of_last_window = 0
    cohort_num = 1
    while True:
        window = take(args.training_window_size, reader)
        print("")
        print(
            "Mining window [{},{}]".format(
                transaction_num,
                transaction_num + len(window)))
        end_of_last_window = transaction_num + len(window)
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

        training_rule_tree = RuleTree()
        for (antecedent, consequent, _, _, _) in rules:
            training_rule_tree.insert(antecedent, consequent)

        transaction_num += len(window)

        # Populate the training rule tree with the rule frequencies from
        # the training window.
        for transaction in window:
            training_rule_tree.record_matches(transaction)

        # Populate the test rule tree with a deep copy of the training set.
        test_rule_tree = deepcopy(training_rule_tree)

        training_match_vec = training_rule_tree.match_vector()

        # Number of transations which we read before collecting another
        # distance sample.
        SAMPLE_INTERVAL = 10

        # Number of samples of the Hellinger distance of the
        # rag-bag/rule-match-vector means we collect before we test against
        # the training set.
        SAMPLE_THRESHOLD = 30

        num_test_transactions = 0
        rule_vec_mean = RollingMean()
        rag_bag_mean = RollingMean()
        for transaction in reader:
            test_rule_tree.record_matches(transaction)

            num_test_transactions += 1
            transaction_num += 1
            if num_test_transactions == SAMPLE_INTERVAL:
                test_match_vec = test_rule_tree.match_vector()
                distance = hellinger(training_match_vec, test_match_vec)
                if rule_vec_mean.n > SAMPLE_THRESHOLD:
                    conf = rule_vec_mean.std_dev() * args.drift_confidence
                    mean = rule_vec_mean.mean()
                    if distance > mean + conf or distance < mean - conf:
                        print(
                            "Distance at transaction {} = {} [lo_bound,avg,up_bound] = [{},{},{}]".format(
                                transaction_num, distance, mean - conf, mean, mean + conf))
                        print(
                            "Change detected in rule-match-vector at transaction {}".format(transaction_num))
                        break
                rule_vec_mean.add_sample(distance)

                rag_bag = hellinger([training_rule_tree.rag_bag()], [
                                    test_rule_tree.rag_bag()])
                if rag_bag_mean.n > SAMPLE_THRESHOLD:
                    conf = rag_bag_mean.std_dev() * args.drift_confidence
                    mean = rag_bag_mean.mean()
                    if rag_bag > mean + conf or rag_bag < mean - conf:
                        print(
                            "rag bag at transaction {} = {} [lo_bound,avg,up_bound] = [{},{},{}]".format(
                                transaction_num, rag_bag, mean - conf, mean, mean + conf))
                        print(
                            "Change detected in rag bag at transaction {}",
                            transaction_num)
                        break
                rag_bag_mean.add_sample(rag_bag)

                # Reset counter, so we loop again.
                num_test_transactions = 0

        print(
            "Detected change {} transactions after end of training window".format(
                transaction_num -
                end_of_last_window))

        if len(window) < args.training_window_size:
            print("End of stream")
            break

    duration = time.time() - program_start
    print("Total runtime {:.2f} seconds".format(duration))

    return 0


if __name__ == "__main__":
    sys.exit(main())
