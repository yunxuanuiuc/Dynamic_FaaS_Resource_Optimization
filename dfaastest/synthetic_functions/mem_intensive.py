import random


def payload_generator():
    n = random.randrange(500000, 1000001)
    return {"array_size": n}
