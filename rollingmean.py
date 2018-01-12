import numpy

class RollingMean:
    def __init__(self):
        self.x_sum = 0
        self.x_sq_sum = 0
        self.n = 0

    def add_sample(self, x):
        self.x_sum += x
        self.x_sq_sum += x ** 2
        self.n += 1

    def mean(self):
        return self.x_sum / self.n

    def std_dev(self):
        mean = self.mean()
        return numpy.sqrt((self.x_sq_sum / self.n) - (mean * mean))
