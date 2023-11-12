from utils.lambda_utils import update_memory


class FunkUpdater(object):

    def __init__(self, funk_config):
        self.funk_config = funk_config

    def update_function_memory(self, memory):
        update_memory(self.funk_config['function_name'], memory)