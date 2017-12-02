from adaptivewindow import AdaptiveWindow
from item import Item
from cdtds import change_detection_transaction_data_streams
from collections import Counter
from fptree import FPTree
import time
from datasetreader import DatasetReader
import sys


test_transactions = (
    [["a", "b", "c"] for _ in range(10)] +
    [["d", "e", "f"] for _ in range(10)]
)


def test_change():
    gen = change_detection_transaction_data_streams(
        test_transactions,
        window_len=5,
        merge_threshold=2,
        min_cut_len=2,
        local_cut_confidence=0.05)
    found_change_at = -1
    for (tree, transaction_num) in gen:
        print("Detected change at tid {}".format(transaction_num))
        found_change_at = transaction_num
    assert(found_change_at == 20)


def test_cdtds():
    reader = DatasetReader("datasets/mushroom.csv")
    gen = change_detection_transaction_data_streams(
        reader,
        window_len=1000,
        merge_threshold=32,
        min_cut_len=32,
        local_cut_confidence=0.05)
    for (_, transaction_num) in gen:
        print("Detected change at tid {}".format(transaction_num))
