from index import InvertedIndex
from item import Item


def test_InvertedIndex():
    data = ("a,b,c,d,e,f\n"
            "g,h,i,j,k,l\n"
            "z,x\n"
            "z,x\n"
            "z,x,y\n"
            "z,x,y,i\n")
    index = InvertedIndex()
    index.load(data)
    assert(index.support({Item("a")}) == 1 / 6)
    assert(index.support({Item("b")}) == 1 / 6)
    assert(index.support({Item("c")}) == 1 / 6)
    assert(index.support({Item("d")}) == 1 / 6)
    assert(index.support({Item("e")}) == 1 / 6)
    assert(index.support({Item("f")}) == 1 / 6)
    assert(index.support({Item("h")}) == 1 / 6)
    assert(index.support({Item("i")}) == 2 / 6)
    assert(index.support({Item("j")}) == 1 / 6)
    assert(index.support({Item("k")}) == 1 / 6)
    assert(index.support({Item("l")}) == 1 / 6)
    assert(index.support({Item("z")}) == 4 / 6)
    assert(index.support({Item("x")}) == 4 / 6)
    assert(index.support({Item("y")}) == 2 / 6)

    sup_zx = index.support({Item("z"), Item("x")})
    assert(sup_zx == 4 / 6)

    sup_zxy = index.support({Item("z"), Item("x"), Item("y")})
    assert(sup_zxy == 2 / 6)

    sup_zxyi = index.support({Item("z"), Item("x"), Item("y"), Item("i")})
    assert(sup_zxyi == 1 / 6)
