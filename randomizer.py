# Gerador Congruente Linear (LCG)

class LCG:
    def __init__(self, seed=42, a=1664525, c=1013904223, M=2**32):
        self.a = a
        self.c = c
        self.M = M
        self.state = seed
        self.count = 0

    def next(self):
        """Gera o próximo número pseudoaleatório normalizado em [0,1)."""
        self.state = (self.a * self.state + self.c) % self.M
        self.count += 1
        return self.state / self.M
