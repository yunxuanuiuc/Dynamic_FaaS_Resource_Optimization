import json
from copy import deepcopy

import requests

from utils.lambda_utils import get_region_name, construct_api_url, get_rest_api


class CmabClient(object):

    request_templates = {
        "Event": {
            "S3": {
                "bucket": "dfaastest-cmab-agent",
                "key": "example.model"
            },
            "action": "recommend",
            "Request": {
            },
            "Keys": {
                "feature_keys": [
                    "bytes"
                ],
                "mem_key": "memory",
                "cost_key": "cost",
                "prob_key": "probability"
            },
            "config": {
                "memory_list": [
                    64,
                    128
                ],
                "objective": "time",
                "features": [
                    "bytes"
                ],
                "model_name": "example"
            }
        }
    }

    request_observe_templates = {
        "Event": {
            "Request": {
                "memory": 0,
                "probability": None,
                "cost": 0,
                "bytes": 0,
            },
        }
    }

    request_recommend_templates = {
        "Event": {
            "Request": {
                "bytes": 1
            },
        }
    }

    probability = 0.0

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

            request_payload = deepcopy(self.request_templates)
            request_payload["Event"]["Request"] = payload["Event"]["Request"]

            print(f'send_request - request_payload: {request_payload}')

            r = requests.post(self.rest_api_url, data=json.dumps(request_payload))

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

    def send_observe(self, payload):
        request_payload = deepcopy(self.request_observe_templates)
        request_payload["Event"]["Request"]["memory"] = payload["memory_size"]
        request_payload["Event"]["Request"]["probability"] = self.probability
        request_payload["Event"]["Request"]["cost"] = 0 - payload["billed_duration"] # negative
        request_payload["Event"]["Request"]["bytes"] = payload["payload_size"]

        print(f'send_observe - request_payload: {request_payload}')

        return self.send_request(request_payload)

    def send_recommend(self, payload):
        request_payload = deepcopy(self.request_recommend_templates)
        request_payload["Event"]["Request"]["bytes"] = payload["payload_size"]

        print(f'send_observe - request_payload: {request_payload}')

        return self.send_request(request_payload)
