from editdistance import levenstein_distance


def test_levenstein_distance():
    tests = [
        ("a", "a", 0),
        ("a", "b", 1),
        ("bat", "cat", 1),
        ("firetruck", "firebird", 5),
        ("kitten", "sitting", 3),
        ("long", "longer", 2),
        ("a", "alphabet", 7),
    ]

    for (a, b, d) in tests:
        assert(levenstein_distance(a, b) == d)
