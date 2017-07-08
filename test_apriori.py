from index import InvertedIndex
from apriori import apriori
from item import ItemSet


if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")


def test_apriori():
    data = ("a,b,c,d,e,f\n"
            "g,h,i,j,k,l\n"
            "z,x\n"
            "z,x\n"
            "z,x,y\n"
            "z,x,y,i\n")

    expectedItemSets = {ItemSet("i"): 2 / 6,
                        ItemSet("z"): 4 / 6,
                        ItemSet("x"): 4 / 6,
                        ItemSet("y"): 2 / 6,
                        ItemSet("xz"): 4 / 6,
                        ItemSet("yz"): 2 / 6,
                        ItemSet("xy"): 2 / 6,
                        ItemSet("xyz"): 2 / 6}

    index = InvertedIndex()
    index.load(data)
    itemsets = apriori(index, 2 / 6)
    assert(set(expectedItemSets.keys()) == set(itemsets))
    for itemset in itemsets:
        assert(expectedItemSets[itemset] == index.support(itemset))
