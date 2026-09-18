class TokenBucket:
    def __init__(self, capacity, refill_per_second):
        raise NotImplementedError

    def allow(self, now, cost=1):
        raise NotImplementedError
