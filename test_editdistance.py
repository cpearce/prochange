from editdistance import levenstein_distance


def test_levenstein_distance():
    tests = [
        ("bat", "cat", 1),
        ("firetruck", "firebird", 5),
        ("kitten", "sitting", 3),
        ("long", "longer", 2),
        ("a", "alphabet", 7),
    ]
