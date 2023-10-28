import json
import urllib.parse
import vowpalwabbit as vw
import boto3
import random
import os

print('Loading function')

s3 = boto3.client('s3')

class optimizer():
    def __init__(self,
                 memory_list: list,
                 optimization_objective: str,
                 features: list,
                 model_name: str,
                 model_path: str
                ):
        """
        this optimizer supports sequential learning (batched learning not supported).
        observations will be fed in one after another to update the model.s
        ------
        memory_list: a sorted list of candidate memory sizes, in ascending order
        optimization_objective: "budget", or "time".
        --TODO: consider supporting weighted sum of different objectives in future
        features: list of the contextual features that the optimizer will take into account when learning
        model_path: the place where the model is stored at and can be loaded from
        """
        self.memories = memory_list # TODO: transform candidates into integers from 1 to N
        self.mem2action = {self.memories[i]: i+1 for i in range(len(self.memories))}
        self.action2mem = {i+1: self.memories[i] for i in range(len(self.memories))}

        self.n_actions = len(self.memories)
        self.minimizing_objective = optimization_objective
        self.features = features
        self.model_name = model_name
        self.model_path = model_path

#         if os.path.exists(os.path.join(self.model_path, self.model_name)):
#             self.model = vw
#         else:
        self.model = vw.Workspace(f"--cb_explore {self.n_actions} --epsilon 0.1", quiet=True, enable_logging=True)
            # TODO: add other hyperparameters here


    def convert_to_vw_format(self,
                             request,
                             feature_keys: list,
                             predict_mode = False,
                             mem_key: str = None,
                             cost_key:str = None,
                             prob_key: str = None):
        """
        Convert the input request to vw-compatible format
        ------
        The request should contain the following input:
            - action: memory size chosen
            - objective function score: cost, or time
            - probability: the probability that this action was chosen
            - features: other features of this request
        """
        if not predict_mode:
            obs = (
            str(self.mem2action[request[mem_key]])
            + ":"
            + str(request[cost_key])
            + ":"
            + str(request[prob_key])
            + " |"
        )
        else:
            obs = "|"

        for key in feature_keys:
            obs += " " + str(request[key])

        return obs

    def observe(self,
                request,
                feature_keys: list = ["bytes"],
                mem_key: str = "memory",
                cost_key:str = "cost",
                prob_key: str = "probability"):
        """
        given a trial which has an action, cost, probability of the action, and features,
        learn the data and update the model
        """
        self.model.learn(self.convert_to_vw_format(request, feature_keys, False, mem_key, cost_key, prob_key))

    @staticmethod
    def sample_custom_pmf(pmf):
        total = sum(pmf)
        scale = 1 / total
        pmf = [x * scale for x in pmf]
        draw = random.random()
        sum_prob = 0.0
        for index, prob in enumerate(pmf):
            sum_prob += prob
            if sum_prob > draw:
                return index, prob

    def recommend(self,
                  request,
                  feature_keys: list = ["bytes"]):
        """
        given an incoming trail with certain features, recommend an memory
        """
        rec_probabilities = self.model.predict(self.convert_to_vw_format(request, feature_keys, True))
        index, prob = self.sample_custom_pmf(rec_probabilities)
        return self.action2mem[index+1]

    def save_model_state(self, s3_obj):
        """
        save the current model for future use
        """
        self.model.save(s3_obj)
    def load_model(self, filepath):
        """
        load and continue to use current model.
        """
        self.model = vw.Workspace(filepath)

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    action = event['Event']['action']
    if action=="create":
        pass
    else:
        bucket = event['Event']['S3']['bucket']
        key = event['Event']['S3']['key']
        model_dir = f"s3://{bucket}"
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            print("CONTENT TYPE: " + response['ContentType'])
      #      return response['ContentType']
        except Exception as e:
            print(e)
            print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
            raise e   
        #todo: support configing these?
        agent = optimizer(
                    memory_list=[64, 128],
                    optimization_objective="time",
                    features=["bytes"],
                    model_name="example",  
                    model_path="")
        try:
            agent.load_model(f"{model_dir}/example.model")
            print("loaded the model!")
            return "success"
        except Exception as e:
            print("did not load the model")
            print(e)
            raise 3
        
    if action=="observe":
        pass
    elif action=="recommend":
        pass
        
    
    # Get the object from the event and show its content type


        