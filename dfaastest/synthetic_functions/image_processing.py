import random


def payload_generator():
    width = random.randrange(1000, 6001)
    height = random.randrange(1000, 4001)
    return {"width": width, "height": height}
