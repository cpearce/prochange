from adaptivewindow import AdaptiveWindow
from item import Item
from cdtds import change_detection_transaction_data_streams
from cdtds import find_local_drift

test_transactions = [
    ["a", "b"],
    ["b", "c", "d"],
    ["a", "c", "d", "e"],
    ["a", "d", "e"],
    ["a", "b", "c"],
    ["a", "b", "c", "d"],
    ["a"],
    ["a", "b", "c"],
    ["a", "b", "d"],
    ["b", "c", "e"],
]


def test_local_drift():
    window = AdaptiveWindow(1)
    num_transactions = 0
    for transaction in [list(map(Item, t)) for t in test_transactions]:
        num_transactions += 1
        window.add(transaction)
        cut_index = find_local_drift(window, 0.5, 2)
        if cut_index is not None:
            assert(cut_index == 1)
            break
    else:
        assert(False)


def test_cdtds():
    change_detection_transaction_data_streams(
        test_transactions, 0.5, 0.5, 1, 2)
