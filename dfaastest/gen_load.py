import argparse
import json
import time
from datetime import datetime
from importlib import import_module
from multiprocessing import Process

import requests

from utils.config_utils import get_funk_names, get_config
from utils.lambda_utils import get_rest_api, construct_api_url, get_region_name


class GenLoad(object):

    def __init__(self,
                 debug=False,
                 funk_name=None,
                 wait_periods=None,
                 dryrun=False,
                 duration=0,
                 funk_config=None,
                 mode=None,
                 ):
        self.debug = debug
        self.funk_name = funk_name
        self.dryrun = dryrun
        self.wait_periods = wait_periods
        self.duration = duration
        self.funk_params = funk_config['params']
        self.funk_config = funk_config
        self.api = get_rest_api(funk_config['api_name'])
        self.api_url = construct_api_url(self.api['id'], get_region_name(), funk_config['api_stage'], funk_config['api_base_path'])
        self.funk_module = import_module(funk_config['module'])
        self.mode = mode

    def send_request(self, api, payload):
        if not self.dryrun:
            r = requests.post(api, data=json.dumps(payload))

            try:
                res = r.json()['body']
            except Exception as e:
                res = r.text

            if self.debug:
                print(f"send_request - response: {res}")

            return res
        else:
            print(f"send_request - api: {api}; payload: {json.dumps(payload)}")
            return None

    def send_workload_request(self):
        payload = self.funk_module.payload_generator()

        self.send_request(api=self.api_url, payload=payload)

    def run(self):
        match self.mode:
            case 'sync': self.run_sync()
            case 'async': self.run_async()

    def run_sync(self):
        start_time = datetime.utcnow()
        print(f'Starting to run - start time: {start_time}...')

        # Will need to kill the process or send it the kill signal
        while (datetime.utcnow() - start_time).total_seconds() < self.duration:

            # for each of the wait periods
            for wait_period in self.wait_periods:
                period_start_time = datetime.utcnow()

                while (datetime.utcnow() - period_start_time).total_seconds() < wait_period['duration']:
                    try:

                        self.send_workload_request()

                        if wait_period['wait'] > 0:
                            time.sleep(wait_period['wait'])

                    except Exception as e:
                        print(f'Exception occurred while sending request: {e}')

        print(f'Ended the run.')

    def run_async(self):
        threads = []

        start_time = end_time = datetime.utcnow()
        print(f'Starting the async run - start time: {start_time}...')

        # Will need to kill the process or send it the kill signal
        while (end_time - start_time).total_seconds() < self.duration:

            # for each of the wait periods
            for wait_period in self.wait_periods:
                period_start_time = datetime.utcnow()

                while (datetime.utcnow() - period_start_time).total_seconds() < wait_period['duration']:
                    try:

                        worker_thread = Process(target=self.send_workload_request(), args=(), daemon=True)
                        worker_thread.start()

                        threads.append(worker_thread)

                        if wait_period['wait'] > 0:
                            time.sleep(wait_period['wait'])

                    except Exception as e:
                        print(f'Exception occurred while sending request: {e}')

            end_time = datetime.utcnow()

        # Make sure the threads complete
        for worker_thread in threads:
            worker_thread.join()

        print(f'Ended the async run - end time: {end_time} - total function runtime duration: {(datetime.utcnow() - start_time).total_seconds()}')

    def test(self):
        print(f'Starting test...')

        self.send_workload_request()

        print(f'Finished test.')


if __name__ == '__main__':

    funk_names = get_funk_names()
    config = get_config()
    funktions_config = config['funk_generator']
    load_gen_config = config['load_generator']

    parser = argparse.ArgumentParser(description='Run the lambda function load generator.')
    parser.add_argument('--action', default="run", choices=['run', 'test'], help='Run system continuously or test a single function')
    parser.add_argument('--dryrun', action='store_true', help='Whether or not to send/use-real requests.')
    parser.add_argument('--funk-name', required=True, choices=funk_names, help='Which function to generate load for?')

    args = parser.parse_args()
    print(f'args: {args}')

    action = args.action
    dryrun = args.dryrun
    funk_name = args.funk_name

    print(f'action: {action}')
    print(f'dryrun: {dryrun}')
    print(f'funk_name: {funk_name}')

    gl = GenLoad(
        debug=load_gen_config['debug'],
        funk_name=funk_name,
        dryrun=dryrun,
        duration=load_gen_config['duration'],
        wait_periods=load_gen_config['wait_periods'],
        funk_config=funktions_config[funk_name],
        mode=load_gen_config['mode'],
    )

    match args.action:
        case 'run':
            gl.run()

        case 'test':
            gl.test()


