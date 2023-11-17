import random


def payload_generator():
    n = random.randrange(1, 128457)
    return {"line_number": n}
