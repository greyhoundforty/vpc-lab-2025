import os
import httpx
from datetime import datetime
from ibm_vpc import VpcV1
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
    service = VpcV1(authenticator=authenticator)
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


def create_vpc(vpc_client, resource_group_id, prefix):
    address_prefix_management = "auto"
    response = vpc_client.create_vpc(
        classic_access=False,
        address_prefix_management="auto",
        name=f"{prefix}-vpc",
        resource_group={"id": resource_group_id},
    ).get_result()
    return response


def create_public_gateways(vpc_client, vpc_id, zone_name, resource_group_id, prefix):
    # Create models directly in the function call
    response = vpc_client.create_public_gateway(
        vpc={"id": vpc_id},
        zone={"name": zone_name},
        name=f"{prefix}-pgw-{zone_name}",
        resource_group={"id": resource_group_id},
    ).get_result()

    return response


def create_subnets(
    vpc_client, public_gateway_id, resource_group_id, vpc_id, zone, prefix
):
    subnet_prototype = {
        "ip_version": "ipv4",
        "name": f"{prefix}-subnet-{zone}",
        "public_gateway": {"id": public_gateway_id} if public_gateway_id else None,
        "resource_group": {"id": resource_group_id},
        "vpc": {"id": vpc_id},
        "total_ipv4_address_count": 128,
        "zone": {"name": zone},
    }

    response = vpc_client.create_subnet(subnet_prototype).get_result()
    return response


def create_tailscale_sg_group(vpc_client, vpc_id, resource_group_id, prefix):
    security_group = vpc_client.create_security_group(
        vpc={"id": vpc_id},
        name=f"{prefix}-security-group",
        resource_group={"id": resource_group_id},
    )
    # security_group_prototype = {
    #     "ip_version": "ipv4",
    #     "name": f"{prefix}-security-group",
    #     "resource_group": {"id": resource_group_id},
    #     "vpc": {"id": vpc_id},
    # }

    response = security_group.get_result()
    return response


def create_rules(vpc_client, sg_id):
    security_group_rule_protocol_tcp_remote_model = {}
    security_group_rule_protocol_tcp_remote_model["cidr_block"] = "100.64.0.0/10"
    security_group_rule_prototype_model = {}
    security_group_rule_prototype_model["direction"] = "inbound"
    security_group_rule_prototype_model["ip_version"] = "ipv4"
    security_group_rule_prototype_model["protocol"] = "icmp"
    security_group_rule_prototype_model["code"] = 0
    security_group_rule_prototype_model["type"] = 8
    security_group_rule_prototype = security_group_rule_prototype_model
    response = vpc_client.create_security_group_rule(
        sg_id, security_group_rule_prototype
    )

    security_group_rule_prototype_model = {}
    security_group_rule_prototype_model["direction"] = "inbound"
    security_group_rule_prototype_model["ip_version"] = "ipv4"
    security_group_rule_prototype_model["protocol"] = "tcp"
    security_group_rule_prototype_model["port_min"] = 22
    security_group_rule_prototype_model["port_max"] = 22
    security_group_rule_prototype_model[
        "remote"
    ] = security_group_rule_protocol_tcp_remote_model
    security_group_rule_prototype = security_group_rule_prototype_model
    response = vpc_client.create_security_group_rule(
        sg_id, security_group_rule_prototype
    )

    security_group_rule_prototype_model = {}
    security_group_rule_prototype_model["direction"] = "inbound"
    security_group_rule_prototype_model["ip_version"] = "ipv4"
    security_group_rule_prototype_model["protocol"] = "tcp"
    security_group_rule_prototype_model["port_min"] = 80
    security_group_rule_prototype_model["port_max"] = 80
    security_group_rule_prototype = security_group_rule_prototype_model
    response = vpc_client.create_security_group_rule(
        sg_id, security_group_rule_prototype
    )

    security_group_rule_prototype_model = {}
    security_group_rule_prototype_model["direction"] = "inbound"
    security_group_rule_prototype_model["ip_version"] = "ipv4"
    security_group_rule_prototype_model["protocol"] = "tcp"
    security_group_rule_prototype_model["port_min"] = 443
    security_group_rule_prototype_model["port_max"] = 443
    security_group_rule_prototype = security_group_rule_prototype_model
    response = vpc_client.create_security_group_rule(
        sg_id, security_group_rule_prototype
    )

    security_group_rule_prototype_model = {}
    security_group_rule_prototype_model["direction"] = "outbound"
    security_group_rule_prototype_model["ip_version"] = "ipv4"
    security_group_rule_prototype_model["protocol"] = "all"
    security_group_rule_prototype = security_group_rule_prototype_model
    response = vpc_client.create_security_group_rule(
        sg_id, security_group_rule_prototype
    )


def create_tailscale_key(token, tailnet_id, tailscale_tag):
    url = f"https://api.tailscale.com/api/v2/tailnet/{tailnet_id}/keys?all=true"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "capabilities": {
            "devices": {
                "create": {
                    "reusable": False,
                    "ephemeral": True,
                    "preauthorized": True,
                    "tags": [f"{tailscale_tag}"],
                }
            }
        },
        "expirySeconds": 86400,
        "description": "Labme access",
    }

    response = httpx.post(url, headers=headers, json=data)
    return response.json()


def create_vnic(vpc_client, subnet_id, resource_group_id, prefix, security_group_id):
    allow_ip_spoofing = False
    security_groups = [{"id": security_group_id}]

    response = vpc_client.create_virtual_network_interface(
        name=f"{prefix}-tailscale-vnic",
        subnet={"id": subnet_id},
        allow_ip_spoofing=allow_ip_spoofing,
        resource_group={"id": resource_group_id},
        security_groups=security_groups,
    )
    virtual_network_interface = response.get_result()

    return virtual_network_interface


# def create_security_groups(region):
#     service = "thing"
#     time.sleep(random.randint(2, 8))
#     return service


# def create_tailscale_token(region):
#     service = "thing"
#     time.sleep(random.randint(2, 8))
#     return service


# def create_tailscale_compute(region):
#     service = "thing"
#     time.sleep(random.randint(2, 8))
#     return service
