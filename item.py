itemNameToId = {}
itemIdToName = {}

class Item:
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("Item name must be string")
        name = name.strip()
        if name not in itemNameToId:
            itemId = len(itemNameToId) + 1
            itemNameToId[name] = itemId
            itemIdToName[itemId] = name
        self.id = itemNameToId[name]

    def __str__(self):
        return itemIdToName[self.id]

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.id

    def __lt__(self, other):
        return itemIdToName[self.id] < itemIdToName[other.id]

    def __hash__(self):
        return self.id