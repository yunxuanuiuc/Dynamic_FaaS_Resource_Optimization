import argparse
import time
from multiprocessing import Process

from cmab_client import CmabClient
from funk_updater import FunkUpdater
from gen_load import GenLoad
from utils.config_utils import get_funk_names, get_config
from worker import DfaastestOperator


class Benchmarker(object):
    """
    Runs the benchmarks:
    - iterates through each of the memory configurations
    - for each memory configuration it will run load for 20 mins
    """

    def __init__(self, config, benchmarker_config, funk_name, funk_config):
        self.funk_name = funk_name
        self.benchmarker_config = benchmarker_config
        self.funk_config = funk_config
        self.config = config

        self.memory_configs = CmabClient.request_templates['Event']['config']['memory_list']
        print(f'Benchmarker.__init__ - self.memory_configs: {self.memory_configs}')

        self.funk_updater = FunkUpdater(self.config['funk_generator'][funk_name])

    def start_worker(self, experiment_id):
        worker = DfaastestOperator(
            config=self.config,
            dryrun=False,
            funk_name=self.funk_name,
            experiment_id=experiment_id,
        )
        worker.benchmark()

    def start_load_generator(self):
        load_generator = GenLoad(
            debug=False,
            funk_name=self.funk_name,
            wait_periods=[{'wait': self.benchmarker_config['wait'], 'duration': self.benchmarker_config['duration']}],
            duration=self.benchmarker_config['duration'],
            funk_config=self.funk_config,
        )
        load_generator.run()

    def run(self):
        print(f"Benchmarker.run - starting...")

        for memory in self.memory_configs:

            # set the memory for this benchmark run
            self.funk_updater.update_function_memory(memory=memory)

            experiment_id = f'benchmark_{self.funk_name}_{memory}'

            worker_thread = Process(target=self.start_worker, args=(experiment_id,), daemon=True)
            worker_thread.start()

            load_generator_thread = Process(target=self.start_load_generator, args=())
            load_generator_thread.start()

            # after this join the worker thread will continue executing indefinitely
            # but we won't care, we'll just let it run and it will be killed when the process exits
            load_generator_thread.join()

            time.sleep(60)  # wait for any worker threads to finish processing records
            worker_thread.terminate()


if __name__ == '__main__':

    funk_names = get_funk_names()
    config = get_config()
    funktions_config = config['funk_generator']

    parser = argparse.ArgumentParser(description='Run the dfaastest benchmarks for a given function, runs the load generator and the worker.')
    parser.add_argument('--action', default="run", choices=['run'], help='Run benchmarker')
    parser.add_argument('--funk-name', required=True, choices=funk_names, help='Which function to benchmark?')

    args = parser.parse_args()
    print(f'args: {args}')

    match args.action:
        case 'run':
            b = Benchmarker(
                config=config,
                benchmarker_config=config['benchmarker'],
                funk_name=args.funk_name,
                funk_config=funktions_config[args.funk_name]
            )
            b.run()
