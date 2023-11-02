import json

import requests

from utils.lambda_utils import get_region_name, construct_api_url, get_rest_api


class CmabClient(object):

    def __init__(self, config, debug=False, dryrun=False):
        print(f"CmabClient")
        self.config = config
        self.debug = debug
        self.dryrun = dryrun

        self.cmab_config = self.config['cmab_agent']

        self.api = get_rest_api(self.cmab_config['api_name'])
        self.rest_api_url = construct_api_url(self.api['id'], get_region_name(), self.cmab_config['api_stage'], self.cmab_config['api_base_path'])

    def send_request(self, payload):
        if not self.dryrun:
            r = requests.post(self.rest_api_url, data=json.dumps(payload))

            try:
                res = r.json()['body']
            except Exception as e:
                res = r.text

            if self.debug:
                print(f"CmabClient.send_request - response JSON body: {res}")

            return res
        else:
            print(f"send_request - api: {self.rest_api_url}; payload: {json.dumps(payload)}")
            return None
