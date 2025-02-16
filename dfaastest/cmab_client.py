import json
from copy import deepcopy

import requests

from utils.lambda_utils import get_region_name, construct_api_url, get_rest_api


class CmabClient(object):
    mem_list = [128, 256, 512, 1024, 2048]
    request_templates = {
        "Event": {
            "S3": {
                "bucket": "dfaastest-cmab-agent",
                "key": None,  # this gets updated by the worker based on the function name and the experiment
            },
            "action": None,
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
                "memory_list": mem_list,
                "objective": "time",
                "features": [
                    "bytes"
                ],
                "model_name": None,  # this gets updated by the worker based on the function name and the experiment
            }
        }
    }

    request_observe_templates = {
        "Event": {
            "action": "observe",
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
            "action": "recommend",
            "Request": {
                "bytes": 1
            },
        }
    }

    # Predicted values (initially set to 0)
    memory = 0
    probability = 0.0

    def __init__(self, cmab_config, debug=False, dryrun=False):
        print(f"CmabClient")
        self.cmab_config = cmab_config
        self.debug = debug
        self.dryrun = dryrun
        #self.mem_list = mem_list

        self.model_funk = self.cmab_config['model_funk']
        self.model_experiment = self.cmab_config['model_experiment']
        self.optimization_goal = self.cmab_config['optimization_goal']
        self.slo = self.cmab_config['slo']

        self.model_name = f"{self.model_funk}_{self.model_experiment}"
        self.request_templates['Event']['S3']['key'] = f"{self.model_name}.model"
        self.request_templates['Event']['config']['model_name'] = self.model_name

        self.api = get_rest_api(self.cmab_config['api_name'])
        self.rest_api_url = construct_api_url(self.api['id'], get_region_name(), self.cmab_config['api_stage'], self.cmab_config['api_base_path'])
        print(f"CmabClient.__init__ - rest_api_url: {self.rest_api_url}")

        # Initialize the client for memory and probability from the CmabAgent
        recommendation = self.send_recommend({"payload_size": 1}) # TODO get a recommendation based on DB data
        print(f"CmabClient.__init__ - recommendation: {recommendation}")
        self.memory = recommendation['recommended_memory']
        self.probability = recommendation['action_probability']
        self.probability_dict = {self.mem_list[i]: recommendation['probability_list'][i] for i in range(len(self.mem_list))}

    def send_request(self, payload):
        if not self.dryrun:

            request_payload = deepcopy(self.request_templates)
            request_payload["Event"] = { **request_payload["Event"], **payload["Event"] }

            print(f'send_request - request_payload: {request_payload}')

            r = requests.post(self.rest_api_url, data=json.dumps(request_payload))

            res = r.json()['body']

            if self.debug:
                print(f"CmabClient.send_request - response JSON body: {res}")

            return res
        else:
            print(f"send_request - api: {self.rest_api_url}; payload: {json.dumps(payload)}")
            return None

    def send_observe(self, payload):
        request_payload = deepcopy(self.request_observe_templates)
        request_payload["Event"]["Request"]["memory"] = payload["memory_size"]
        request_payload["Event"]["Request"]["probability"] = self.probability_dict[payload["memory_size"]]

        match self.optimization_goal:
            case 'billed_duration':
                request_payload["Event"]["Request"]["cost"] = 1000/int(payload["billed_duration"])  # 300*1/time
            case 'slo':
                cost = int(payload["billed_duration"])
                slo = self.slo[self.model_funk]
                if cost > slo:
                    cost = 1/cost  # penalization
                else:
                    cost = slo - cost
                request_payload["Event"]["Request"]["cost"] = cost

        request_payload["Event"]["Request"]["bytes"] = payload["payload_size"]

        print(f'send_observe - request_payload: {request_payload}')

        return self.send_request(request_payload)

    def send_recommend(self, payload):
        request_payload = deepcopy(self.request_recommend_templates)
        request_payload["Event"]["Request"]["bytes"] = payload["payload_size"]

        print(f'send_recommend - request_payload: {request_payload}')

        recommendation_response = self.send_request(request_payload)
        print(f'send_recommend - response: {recommendation_response}')
        return recommendation_response['result']
