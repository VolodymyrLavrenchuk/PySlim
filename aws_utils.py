import logging
import json
import boto3

_LOGGER_NAME = 'PySlim'

class AwsLambdaUtils:

    def invoke(self, function_name, invocation_type = 'RequestResponse', payload = {}):       
        client = boto3.client('lambda')
        logging.getLogger(_LOGGER_NAME).info("Invoke: " + function_name)

        response = client.invoke(
            FunctionName = function_name,
            InvocationType = invocation_type,
            Payload = json.dumps(payload),
        )
        logging.getLogger(_LOGGER_NAME).info(response)
        return response.get('StatusCode')