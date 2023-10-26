import argparse
import json
import requests
import time
from datetime import datetime

# CONFIG VARIABLES
config = {
    'debug': False,
    'duration': 5,             # number of seconds for the run
    'wait_period': 100 / 1000, # in seconds, for the number of milliseconds divide by 1000 (ms/s)
    'workload_requests_params': {
        'low': {
            'payload': { },
            'api': 'TBD',
        },
        'high': {
            'payload': { },
            'api': 'TBD',
        },
    }
}


class GenLoad(object):

    def __init__(self,
                 debug=False,
                 workload_requests_params=None,
                 wait_period=0,
                 workload=None,
                 dryrun=False,
                 duration=0):
        self.debug = debug
        self.workload_requests_params = workload_requests_params
        self.workload = workload
        self.dryrun = dryrun
        self.wait_period = wait_period
        self.duration = duration

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

    def send_low_workload_request(self):
        rp = self.workload_requests_params['low']
        self.send_request(api = rp['api'], payload = rp['payload'])

    def send_high_workload_request(self):
        rp = self.workload_requests_params['high']
        self.send_request(api = rp['api'], payload = rp['payload'])

    def send_workload_request(self):
        match self.workload:
            case 'low': self.send_low_workload_request()
            case 'hih': self.send_high_workload_request()

    def run(self):
        start_time = datetime.utcnow()
        print(f'Starting to run - start time: {start_time}...')

        # Will need to kill the process or send it the kill signal
        while (datetime.utcnow() - start_time).total_seconds() < self.duration:
            try:

                match self.workload:
                    case 'low': self.send_low_workload_request()
                    case 'hih': self.send_high_workload_request()

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

    parser = argparse.ArgumentParser(description='Run the lambda function load generator.')
    parser.add_argument('--action', default="run", choices=['run', 'test'], help='Run system continuously or test a single function')
    parser.add_argument('--dryrun', action='store_true', help='Whether or not to send/use-real requests.')
    parser.add_argument('--workload', required=True, choices=['low', 'high'], help='Which function to run.')

    args = parser.parse_args()
    print(f'args: {args}')

    action = args.action
    dryrun = args.dryrun
    workload = args.workload

    print(f'action: {action}')
    print(f'dryrun: {dryrun}')
    print(f'workload: {workload}')

    gl = GenLoad(
        debug=config['debug'],
        workload_requests_params=config['workload_requests_params'],
        workload=workload,
        dryrun=dryrun,
        duration=config['duration']
    )

    match args.action:
        case 'run':
            gl.run()

        case 'test':
            gl.test()


