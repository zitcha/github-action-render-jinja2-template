import jinja2
import boto3
import botocore
import json
import sys
import os
import requests

"""
    This python script renders a template in the Jinja2 (https://jinja.palletsprojects.com/)
    However the default control characters of {{  {%  and  {#  have been replaced
    with  <<<  <<%  and  <<#

    How to execute this script on local development environment:

    AWS_PROFILE=zitcha ENV_NAME=bt01 python3 render-j2-template.py .env.deployment.j2

    In this example, the local AWS Profile 'zitcha' will be used to access AWS Secrets Manager.
    The "ENV_NAME" will be "beta" and the template file name is ".env_vars.deployment.j2"

    A few extra features have been added to extend the functionality of the template:

    <<< by_env(staging='value_specific_to_staging', production='value_specific_to_production', default='default_for_all_other_environments') >>>
    This allow different values to be specified for each environment. If no value is provided for a particular value, the default is used.

    <<< parameter_store('/some/param') >>>
    Gets a parameter from AWS Parameter Store

    <<< environmental_vars('MY_ENV') >>>
    This behaves the same as os.getenv() in regular python code ( https://docs.python.org/3/library/os.html#os.getenv )
    Remember this will refer to the variables of the BUILD ENVIRONMENT

    <<< env_name >>>
    Get the "Zitcha Environment" which is the same as the current Git branch. This is equivalent to <<<env_vars('GITHUB_REF_NAME')>>>

    <<< fnd_name >>>
    <<< org_name >>>

    All other features of Jinja2 should be available in the template
"""

#
# Function definitions
#
def by_env(**kwargs):
    if ENV_NAME in kwargs:
        return kwargs[ENV_NAME]

    if 'default' in kwargs:
        return kwargs['default']

    raise Exception('No value provided for environment "' + ENV_NAME + '" and no default provided either')

parameter_store_cache = {}
def get_parameter_store(parameter_store_name):
    if parameter_store_name not in parameter_store_cache:
        client = boto3.client('ssm')
        try:
            parameter_store_cache[parameter_store_name] = client.get_parameter(Name=parameter_store_name)['Parameter']['Value']
        except client.exceptions.ParameterNotFound as error:
        # except botocore.errorfactory.ParameterNotFound:
        #     print("HEY")
            sys.exit('Cannot find AWS Parameter Store param called ' + parameter_store_name)


    return parameter_store_cache[parameter_store_name]

def get_env_param(parameter_store_name_end):
    return get_parameter_store('/env-' + ENV_NAME + '/' + parameter_store_name_end)

def get_fnd_param(parameter_store_name_end):
    return get_parameter_store('/fnd-' + FND_NAME + '/' + parameter_store_name_end)

def get_org_param(parameter_store_name_end):
    return get_parameter_store('/org-' + ORG_NAME + '/' + parameter_store_name_end)

aws_secrets_manager_cache = {}
def get_aws_secret(secret_name):

    if secret_name not in aws_secrets_manager_cache:
        client = boto3.client('secretsmanager')
        try:
            raw_value = client.get_secret_value(SecretId=secret_name)['SecretString']

            try:
                aws_secrets_manager_cache[secret_name] = json.loads(raw_value)
            except json.decoder.JSONDecodeError:
                sys.exit('Found secret "' + secret_name + '" but cannot decode it as JSON')

        except client.exceptions.ResourceNotFoundException:
            sys.exit('Cannot find AWS Secret called "' + secret_name + '"')

    return aws_secrets_manager_cache[secret_name]

def get_organization_secrets():
    return get_aws_secret(get_org_param('secrets-manager/main'))

def get_foundation_secrets():
    return get_aws_secret(get_fnd_param('secrets-manager/main'))

def get_database_secret():
    return get_aws_secret(get_fnd_param('secrets-manager/database'))

def get_environment_secrets():
    return get_aws_secret(get_env_param('secrets-manager/main'))


def get_gh_secret(secret_name):
    response = requests.get('https://api.github.com/orgs/the-pistol/actions/secrets/' + secret_name,
                            headers={
                                'Accept': 'application/vnd.github+json',
                                'Authorization': 'Bearer ' + os.environ.get('GITHUB_TOKEN'), # GITHUB_TOKEN is set by GitHub actions
                                'X-GitHub-Api-Version': '2022-11-28'
                            })

    return response.content


#
# Determine ENV_NAME, FND_NAME and ORG_NAME
#

ENV_NAME = os.environ.get('ENV_NAME')

if ENV_NAME is None:
    sys.exit('Environmental variable ENV_NAME is not set')

if not ENV_NAME:
    sys.exit('Environmental variable ENV_NAME seems to be an empty value')

FND_NAME = get_env_param('fnd-name')

if not FND_NAME:
    sys.exit('Cannot determine FND_NAME')

ORG_NAME = get_fnd_param('org-name')

if not ORG_NAME:
    sys.exit('Cannot determine ORG_NAME')



#
# Get name of the template file from the command line arguments
#
if len(sys.argv) != 2:
    raise Exception("You must pass the path of a template file")
template_file_name = sys.argv[1]

#
# Configure Jinja2
#
j2env = jinja2.Environment(
    loader=jinja2.FileSystemLoader('.'),
    undefined=jinja2.StrictUndefined,
    block_start_string='<<%',
    block_end_string='%>>',
    variable_start_string='<<<',
    variable_end_string='>>>',
    comment_start_string='<<#',
    comment_end_string='#>>',
)

j2env.globals.update(
    by_env=by_env,
    environmental_vars=os.getenv,

    env_param=get_env_param,
    fnd_param=get_fnd_param,
    org_param=get_org_param,

    aws_secret=get_aws_secret,
    database_secret=get_database_secret,
    environment_secrets=get_environment_secrets,
    foundation_secrets=get_foundation_secrets,
    organization_secrets=get_organization_secrets,
    env_name=ENV_NAME,
    fnd_name=FND_NAME,
    org_name=ORG_NAME
)

#
# Render the Jinja2 Template
#
template = j2env.get_template(template_file_name)
print(template.render())
