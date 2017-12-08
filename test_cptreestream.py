from fptree import FPTree
from fptree import mine_fp_tree
from cptreestream import mine_cp_tree_stream
from datasetreader import DatasetReader
import sys


def test_cp_tree_stream():
    # (csvFilePath, min_support, sort_interval, window_size)
    datasets = [
        ("datasets/UCI-zoo.csv", 0.3, 10, 20),
        ("datasets/mushroom.csv", 0.4, 500, 500),
        # ("datasets/BMS-POS.csv", 0.05, 50000, 50000),
    ]
    for (csvFilePath, min_support, sort_interval, window_size) in datasets:
        transactions = list(DatasetReader(csvFilePath))
        print("test_cp_tree_stream {}".format(csvFilePath))
        for (
                window_start_index,
                window_length,
                cptree_itemsets,
                supports) in mine_cp_tree_stream(
                    transactions,
                    min_support,
                    sort_interval,
                    window_size):
            print("Window {} + {} / {}".format(window_start_index,
                                               window_size, len(transactions)))
            window = transactions[window_start_index:
                                  window_start_index + window_length]
            print("window={}".format(window))
            (fptree_itemsets, supports) = mine_fp_tree(window, min_support)
            print(
                "fptree produced {} itemsets, cptree produced {} itemsets".format(
                    len(fptree_itemsets),
                    len(cptree_itemsets)))
            assert(len(cptree_itemsets) == len(fptree_itemsets))
            assert(set(cptree_itemsets) == set(fptree_itemsets))
