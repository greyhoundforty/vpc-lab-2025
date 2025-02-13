import os
import subprocess
from datetime import datetime
import ibm_vpc
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core.api_exception import ApiException
from ibm_platform_services.resource_controller_v2 import *
from ibm_platform_services import IamIdentityV1, ResourceManagerV2

ibmcloud_api_key = os.environ.get("IBMCLOUD_API_KEY")
if not ibmcloud_api_key:
    raise ValueError("IBMCLOUD_API_KEY environment variable not found")

def ibm_client():  
  authenticator = IAMAuthenticator(ibmcloud_api_key)
  iamIdentityService = IamIdentityV1(authenticator=authenticator)
  return iamIdentityService

def getAccountId():
    try:
        client = ibm_client()
        api_key = client.get_api_keys_details(
          iam_api_key=ibmcloud_api_key
        ).get_result()
    except ApiException as e:
        logging.error("API exception {}.".format(str(e)))
        quit(1)
    account_id = api_key["account_id"]
    return account_id

def resource_controller_service():
    authenticator = IAMAuthenticator(ibmcloud_api_key)
    return ResourceControllerV2(authenticator=authenticator)

def resource_manager_service():
    authenticator = IAMAuthenticator(ibmcloud_api_key)
    return ResourceManagerV2(authenticator=authenticator)


def vpc_client(ibmcloud_api_key, region):
    authenticator = IAMAuthenticator(ibmcloud_api_key)
    service = ibm_vpc.VpcV1(authenticator=authenticator)
    service.set_service_url(f'https://{region}.iaas.cloud.ibm.com/v1')
    return service


def get_group_id_by_name(resource_group_name):
    # rc_service = resource_controller_service()
    rm_service = resource_manager_service()
    account_id = getAccountId()
    resource_groups = rm_service.list_resource_groups(
        account_id=account_id,
    ).get_result()

    for group in resource_groups['resources']:
        if group['name'] == resource_group_name:
            return group['id']
            
    return None

