import csv
from item import Item


class DatasetReader:
    def __init__(self, csv_file_path):
        self.csv_file_path = csv_file_path

    def __iter__(self):
        return map(lambda txn: list(set(map(Item, txn))),
                   csv.reader(open(self.csv_file_path, newline='')))
