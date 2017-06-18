from adaptivewindow import AdaptiveWindow
from item import Item
from cdtds import change_detection_transaction_data_streams
from collections import Counter
from fptree import FPTree
import time
import csv
import sys

def test_cdtds():
    csvFilePath = "datasets/mushroom.csv"
    with open(csvFilePath, newline='') as csvfile:
        test_transactions = list(csv.reader(csvfile))
        change_detection_transaction_data_streams(
            test_transactions,
            merge_threshold=32,
            min_cut_len=32,
            local_cut_confidence=0.05,
            global_cut_confidence=0.05)
