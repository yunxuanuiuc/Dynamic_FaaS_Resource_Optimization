import random


def payload_generator():
    n = random.randrange(5, 11)
    return {"factorial_of": n}
