def levenstein_distance(a, b):
    # d[i][j] holds the levenstein distance between the first i elements
    # of a and the first j elements of b.
    d = [[0]*(len(a) + 1)] * (len(b) + 1)

    # Prefixes can be transformed to empty string by dropping all elements.
    for i in range(1, len(a) + 1):
        d[0][i] = i
    for j in range(1, len(b) + 1):
        d[j][0] = i

    for i in range(1, len(a)):
        for j in range(1, len(b)):
            cost = 0 if a[i-1] == b[j-1] else 1
            d[i][j] = min(d[i][j-1], # deletion
                          d[i-1][j], # insertion
                          d[i-1][j-1] + cost) # substitution
    return d[len(a)][len(b)]

