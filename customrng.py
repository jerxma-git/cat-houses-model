import math
import time
from scipy.special import erf, erfinv

class CustomRNG:
    # Реализован как LCG генератор
    m: int      # модуль
    a: int      # множитель
    c: int      # инкремент 
    state: int  # текущее состояние
    def __init__(self, seed=None):
        self.m = 2**32
        self.a = 1664525 
        self.c = 1013904223
        self.state = seed if seed is not None else int(time.time() * 1000) % self.m
    
    def uniform(self):
        self.state = (self.a * self.state + self.c) % self.m
        return self.state / self.m
    
    def randint(self, a, b):
        return a + int(self.uniform() * (b - a + 1))
    
    def exponential(self, scale):
        u = 1 - self.uniform() # избегаем 0
        return -scale * math.log(u)
    
    def normal(self, mu, sigma):
        u1 = 1 - self.uniform() 
        u2 = self.uniform()
        z0 = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        return mu + z0 * sigma
    
    def truncated_normal(self, mu, sigma, a, b):
        if a >= b:
            raise ValueError("Upper bound must be greater than lower bound")
        
        alpha = (a - mu) / sigma
        beta = (b - mu) / sigma
        
        phi_alpha = 0.5 * (1 + erf(alpha / math.sqrt(2)))
        phi_beta = 0.5 * (1 + erf(beta / math.sqrt(2)))
        
        u = self.uniform()
        phi_u = phi_alpha + u * (phi_beta - phi_alpha)
        
        z = math.sqrt(2) * erfinv(2 * phi_u - 1)
        return mu + z * sigma