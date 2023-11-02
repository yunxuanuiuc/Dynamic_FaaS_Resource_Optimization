import argparse
import json
import requests
import time
from datetime import datetime

from utils.lambda_utils import get_rest_api, construct_api_url, get_region_name
from utils.config_utils import get_funk_names, get_load_generator_config, get_config


class GenLoad(object):

    def __init__(self,
                 debug=False,
                 funk_name=None,
                 wait_period=0,
                 workload=None,
                 dryrun=False,
                 duration=0,
                 funk_config=None
                 ):
        self.debug = debug
        self.funk_name = funk_name
        self.workload = workload
        self.dryrun = dryrun
        self.wait_period = wait_period
        self.duration = duration
        self.funk_params = funk_config['params']
        self.funk_config = funk_config
        self.api = get_rest_api(funk_config['api_name'])
        self.api_url = construct_api_url(self.api['id'], get_region_name(), funk_config['api_stage'], funk_config['api_base_path'])

    def send_request(self, api, payload):
        if not self.dryrun:
            r = requests.post(api, data=json.dumps(payload))
            res = r.json()['body']

            if self.debug:
                print(f"send_request - response JSON body: {res}")

            return res
        else:
            print(f"send_request - api: {api}; payload: {json.dumps(payload)}")
            return None

    def send_workload_request(self):
        self.send_request(api = self.api_url, payload = None)

    def run(self):
        start_time = datetime.utcnow()
        print(f'Starting to run - start time: {start_time}...')

        # Will need to kill the process or send it the kill signal
        while (datetime.utcnow() - start_time).total_seconds() < self.duration:
            try:

                self.send_workload_request()

                if self.wait_period > 0:
                    time.sleep(self.wait_period)

            except Exception as e:
                print(f'Exception ocurred while sending request: {e}')

        print(f'Ended the run.')

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
    parser.add_argument('--funk-name', required=True, choices=funk_names, help='Which function to run.')

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
        wait_period=load_gen_config['wait_period'],
        funk_config=funktions_config[funk_name]
    )

    match args.action:
        case 'run':
            gl.run()

        case 'test':
            gl.test()


