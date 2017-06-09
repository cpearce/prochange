import sys

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")


def levenstein_distance(a, b):
    # d[i][j] holds the levenstein distance between the first i elements
    # of a and the first j elements of b.
    d = [[0 for i in range(len(a) + 1)] for j in range(len(b) + 1)]

    # Prefixes can be transformed to empty string by dropping all elements.
    for i in range(1, len(a) + 1):
        d[0][i] = i
    for j in range(1, len(b) + 1):
        d[j][0] = j

    for j in range(1, len(b) + 1):
        for i in range(1, len(a) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[j][i] = min(d[j - 1][i] + 1,  # deletion
                          d[j][i - 1] + 1,  # insertion
                          d[j - 1][i - 1] + cost)  # substitution

    return d[len(b)][len(a)]

