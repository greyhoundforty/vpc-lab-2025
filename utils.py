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
        api_key = client.get_api_keys_details(iam_api_key=ibmcloud_api_key).get_result()
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
    service.set_service_url(f"https://{region}.iaas.cloud.ibm.com/v1")
    return service


def get_group_id_by_name(resource_group_name):
    # rc_service = resource_controller_service()
    rm_service = resource_manager_service()
    account_id = getAccountId()
    resource_groups = rm_service.list_resource_groups(
        account_id=account_id,
    ).get_result()

    for group in resource_groups["resources"]:
        if group["name"] == resource_group_name:
            return group["id"]

    return None


def create_vpc(vpc_client, resource_group_name, prefix):
    resource_group_identity_model = {}
    resource_group_identity_model["id"] = get_group_id_by_name(resource_group_name)
    resource_group_id = resource_group_identity_model
    vpc_name = f"{prefix}-vpc"
    address_prefix_management = "auto"
    response = vpc_client.create_vpc(
        classic_access=False,
        address_prefix_management=address_prefix_management,
        name=vpc_name,
        resource_group=resource_group_id,
    ).get_result()
    return response


def create_public_gateways(vpc_client, vpc_id, zone_name, resource_group_id, prefix):
    vpc_identity_model = {}
    vpc_identity_model["id"] = vpc_id

    zone_identity_model = {}
    zone_identity_model["name"] = zone_name

    resource_group_identity_model = {}
    resource_group_identity_model["id"] = resource_group_id

    vpc = vpc_identity_model
    zone = zone_identity_model
    name = f"{prefix}-pgw-{zone}"
    resource_group = resource_group_identity_model
    response = vpc_client.create_public_gateway(
        vpc,
        zone,
        name=name,
        resource_group=resource_group,
    ).get_result()

    return response


def create_subnets(
    vpc_client,
    network_acl_id,
    public_gateway_id,
    resource_group_id,
    vpc_id,
    zone,
    prefix,
):
    network_acl_identity_model = {}
    network_acl_identity_model["id"] = network_acl_id

    public_gateway_identity_model = {}
    public_gateway_identity_model["id"] = public_gateway_id

    resource_group_identity_model = {}
    resource_group_identity_model["id"] = resource_group_id

    vpc_identity_model = {}
    vpc_identity_model["id"] = vpc_id

    zone_identity_model = {}
    zone_identity_model["name"] = zone

    subnet_prototype_model = {}
    subnet_prototype_model["ip_version"] = "both"
    subnet_prototype_model["name"] = f"{prefix}-subnet-{zoneName}"
    subnet_prototype_model["network_acl"] = network_acl_identity_model
    subnet_prototype_model["public_gateway"] = public_gateway_identity_model
    subnet_prototype_model["resource_group"] = resource_group_identity_model
    subnet_prototype_model["vpc"] = vpc_identity_model
    subnet_prototype_model["total_ipv4_address_count"] = 128
    subnet_prototype_model["zone"] = zone_identity_model

    subnet_prototype = subnet_prototype_model

    response = vpc_client.create_subnet(subnet_prototype).get_result()
    return response


def create_security_groups(region):
    service = "thing"
    time.sleep(random.randint(2, 8))
    return service


def create_tailscale_token(region):
    service = "thing"
    time.sleep(random.randint(2, 8))
    return service


def create_tailscale_compute(region):
    service = "thing"
    time.sleep(random.randint(2, 8))
    return service
