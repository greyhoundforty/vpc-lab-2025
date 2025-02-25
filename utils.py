import os
import httpx
import base64
from datetime import datetime
from ibm_vpc import VpcV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core.api_exception import ApiException
from ibm_platform_services.resource_controller_v2 import *
from ibm_platform_services import IamIdentityV1, ResourceManagerV2

from jinja2 import Environment, FileSystemLoader

ibmcloud_api_key = os.environ.get("IBMCLOUD_API_KEY")
if not ibmcloud_api_key:
    raise ValueError("IBMCLOUD_API_KEY environment variable not found")


def ibm_client():
    """
    Initializes and returns an instance of the IamIdentityV1 service.

    This function uses the IBM Cloud SDK to create an IAM Identity Service client,
    which can be used to interact with the IBM Cloud Identity and Access Management (IAM) service.
    It relies on the `IBMCLOUD_API_KEY` environment variable for authentication.

    Returns:
        IamIdentityV1: An instance of the IamIdentityV1 service.

    Raises:
        ValueError: If the `IBMCLOUD_API_KEY` environment variable is not set.
    """
    authenticator = IAMAuthenticator(ibmcloud_api_key)
    iamIdentityService = IamIdentityV1(authenticator=authenticator)
    return iamIdentityService


def getAccountId():
    """
    Retrieves the account ID associated with the provided IBM Cloud API key.

    This function uses the IamIdentityV1 service to retrieve details about the API key
    specified in the `IBMCLOUD_API_KEY` environment variable. It then extracts and returns
    the account ID from the API key details.

    Returns:
        str: The account ID associated with the IBM Cloud API key.

    Raises:
        ApiException: If there is an error while calling the IBM Cloud API.
        ValueError: If the `IBMCLOUD_API_KEY` environment variable is not set.
    """
    try:
        client = ibm_client()
        api_key = client.get_api_keys_details(iam_api_key=ibmcloud_api_key).get_result()
    except ApiException as e:
        logging.error("API exception {}.".format(str(e)))
        quit(1)
    account_id = api_key["account_id"]
    return account_id


def resource_controller_service():
    """
    Initializes and returns an instance of the ResourceControllerV2 service.

    This function uses the IBM Cloud SDK to create a Resource Controller service client,
    which can be used to interact with the IBM Cloud Resource Controller service.
    It relies on the `IBMCLOUD_API_KEY` environment variable for authentication.

    Returns:
        ResourceControllerV2: An instance of the ResourceControllerV2 service.

    Raises:
        ValueError: If the `IBMCLOUD_API_KEY` environment variable is not set.
    """
    authenticator = IAMAuthenticator(ibmcloud_api_key)
    return ResourceControllerV2(authenticator=authenticator)


def resource_manager_service():
    """
    Initializes and returns an instance of the ResourceManagerV2 service.

    This function uses the IBM Cloud SDK to create a Resource Manager service client,
    which can be used to interact with the IBM Cloud Resource Manager service.
    It relies on the `IBMCLOUD_API_KEY` environment variable for authentication.

    Returns:
        ResourceManagerV2: An instance of the ResourceManagerV2 service.

    Raises:
        ValueError: If the `IBMCLOUD_API_KEY` environment variable is not set.
    """
    authenticator = IAMAuthenticator(ibmcloud_api_key)
    return ResourceManagerV2(authenticator=authenticator)


def vpc_client(ibmcloud_api_key, region):
    """
    Initializes and returns an instance of the VpcV1 service for a specific region.

    This function uses the IBM Cloud SDK to create a VPC service client, which can be
    used to interact with the IBM Cloud VPC service in a specific region.
    It relies on the `IBMCLOUD_API_KEY` environment variable for authentication.

    Args:
        ibmcloud_api_key (str): The IBM Cloud API key.
        region (str): The IBM Cloud region to target (e.g., "us-south").

    Returns:
        VpcV1: An instance of the VpcV1 service.

    Raises:
        ValueError: If the `IBMCLOUD_API_KEY` environment variable is not set.
    """
    authenticator = IAMAuthenticator(ibmcloud_api_key)
    service = VpcV1(authenticator=authenticator)
    service.set_service_url(f"https://{region}.iaas.cloud.ibm.com/v1")
    return service


def get_group_id_by_name(resource_group_name):
    """
    Retrieves the ID of a resource group by its name.

    This function uses the Resource Manager service to list all resource groups
    in the account and then iterates through the list to find the resource group
    with the specified name.

    Args:
        resource_group_name (str): The name of the resource group to find.

    Returns:
        str: The ID of the resource group if found, otherwise None.

    Raises:
        ApiException: If there is an error while calling the IBM Cloud API.
        ValueError: If the `IBMCLOUD_API_KEY` environment variable is not set.
    """
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
    """
    Creates a VPC (Virtual Private Cloud).

    This function uses the VPC service to create a new VPC with the specified parameters.

    Args:
        vpc_client (VpcV1): An instance of the VpcV1 service.
        resource_group_id (str): The ID of the resource group to create the VPC in.
        prefix (str): A prefix to use for the VPC name.

    Returns:
        dict: The response from the VPC service, containing details about the created VPC.

    Raises:
        ApiException: If there is an error while calling the IBM Cloud API.
        ValueError: If the `IBMCLOUD_API_KEY` environment variable is not set.
    """
    address_prefix_management = "auto"
    response = vpc_client.create_vpc(
        classic_access=False,
        address_prefix_management="auto",
        name=f"{prefix}-vpc",
        resource_group={"id": resource_group_id},
    ).get_result()
    return response


def create_public_gateways(vpc_client, vpc_id, zone_name, resource_group_id, prefix):
    """
    Creates a public gateway in a specific zone.

    This function uses the VPC service to create a public gateway associated with the specified VPC and zone.

    Args:
        vpc_client (VpcV1): An instance of the VpcV1 service.
        vpc_id (str): The ID of the VPC to associate the public gateway with.
        zone_name (str): The name of the zone to create the public gateway in (e.g., "us-south-1").
        resource_group_id (str): The ID of the resource group to create the public gateway in.
        prefix (str): A prefix to use for the public gateway name.

    Returns:
        dict: The response from the VPC service, containing details about the created public gateway.

    Raises:
        ApiException: If there is an error while calling the IBM Cloud API.
        ValueError: If the `IBMCLOUD_API_KEY` environment variable is not set.
    """
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
    """
    Creates a subnet in a specific zone.

    This function uses the VPC service to create a subnet associated with the specified VPC, zone and public gateway.

    Args:
        vpc_client (VpcV1): An instance of the VpcV1 service.
        public_gateway_id (str): The ID of the public gateway to associate the subnet with.
        resource_group_id (str): The ID of the resource group to create the subnet in.
        vpc_id (str): The ID of the VPC to associate the subnet with.
        zone (str): The name of the zone to create the subnet in (e.g., "us-south-1").
        prefix (str): A prefix to use for the subnet name.

    Returns:
        dict: The response from the VPC service, containing details about the created subnet.

    Raises:
        ApiException: If there is an error while calling the IBM Cloud API.
        ValueError: If the `IBMCLOUD_API_KEY` environment variable is not set.
    """
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
    """
    Creates a security group for Tailscale.

    This function uses the VPC service to create a security group associated with the specified VPC.

    Args:
        vpc_client (VpcV1): An instance of the VpcV1 service.
        vpc_id (str): The ID of the VPC to associate the security group with.
        resource_group_id (str): The ID of the resource group to create the security group in.
        prefix (str): A prefix to use for the security group name.

    Returns:
        dict: The response from the VPC service, containing details about the created security group.

    Raises:
        ApiException: If there is an error while calling the IBM Cloud API.
    """
    security_group = vpc_client.create_security_group(
        vpc={"id": vpc_id},
        name=f"{prefix}-security-group",
        resource_group={"id": resource_group_id},
    )

    response = security_group.get_result()
    return response


def create_rules(vpc_client, sg_id):
    """
    Creates security group rules for a given security group.

    This function adds several inbound and outbound rules to the specified security group.
    The rules allow ICMP, SSH (port 22) from Tailscale's network, HTTP (port 80), HTTPS (port 443),
    and all outbound traffic.

    Args:
        vpc_client (VpcV1): An instance of the VpcV1 service.
        sg_id (str): The ID of the security group to add the rules to.

    Raises:
        ApiException: If there is an error while calling the IBM Cloud API.
    """
    security_group_rule_protocol_tcp_tailscale_model = {}
    security_group_rule_protocol_tcp_tailscale_model["cidr_block"] = "100.64.0.0/10"
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
    ] = security_group_rule_protocol_tcp_tailscale_model
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
    """
    Creates a Tailscale API key with specific capabilities.

    This function uses the Tailscale API to create a new API key with the specified
    capabilities, including the ability to create devices with preauthorization and tags.

    Args:
        token (str): The Tailscale API token.
        tailnet_id (str): The ID of the Tailscale tailnet.
        tailscale_tag (str): The tag to apply to devices created with this key.

    Returns:
        dict: The JSON response from the Tailscale API, containing details about the created key.

    Raises:
        httpx.HTTPError: If there is an error while calling the Tailscale API.
    """
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
    """
    Creates a virtual network interface (VNIC).

    This function uses the VPC service to create a new VNIC in the specified subnet,
    associated with the given resource group and security group.

    Args:
        vpc_client (VpcV1): An instance of the VpcV1 service.
        subnet_id (str): The ID of the subnet to create the VNIC in.
        resource_group_id (str): The ID of the resource group to create the VNIC in.
        prefix (str): A prefix to use for the VNIC name.
        security_group_id (str): The ID of the security group to associate with the VNIC.

    Returns:
        dict: The response from the VPC service, containing details about the created VNIC.

    Raises:
        ApiException: If there is an error while calling the IBM Cloud API.
    """
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


def get_latest_ubuntu(vpc_client):
    """
    Retrieves the ID of the latest Ubuntu 24.04 amd64 image.

    This function uses the VPC service to list all available public images and then
    filters the list to find the latest Ubuntu 24.04 amd64 image.

    Args:
        vpc_client (VpcV1): An instance of the VpcV1 service.

    Returns:
        str: The ID of the latest Ubuntu 24.04 amd64 image.

    Raises:
        ApiException: If there is an error while calling the IBM Cloud API.
    """
    all_images = vpc_client.list_images(
        limit=100,
        status=["available"],
        visibility="public",
        user_data_format=["cloud_init"],
    ).get_result()["images"]

    ubuntu_24_images = [
        image
        for image in all_images
        if image.get("name", "").startswith("ibm-ubuntu-24")
        and image.get("operating_system", {}).get("architecture") == "amd64"
    ]

    image_id = ubuntu_24_images[0]["id"]
    return image_id


def create_new_instance(
    vpc_client,
    prefix,
    sg_id,
    resource_group_id,
    vpc_id,
    zone,
    image_id,
    my_key_id,
    first_subnet_id,
    tailscale_device_token,
    first_subnet_cidr,
):
    """
    Creates a new compute instance.

    This function creates a new compute instance in the specified VPC, subnet, and zone.

    Args:
        vpc_client (VpcV1): An instance of the VpcV1 service.
        prefix (str): A prefix to use for the instance name.
        sg_id (str): The ID of the security group to associate with the instance.
        resource_group_id (str): The ID of the resource group to create the instance in.
        vpc_id (str): The ID of the VPC to create the instance in.
        zone (str): The name of the zone to create the instance in (e.g., "us-south-1").
        image_id (str): The ID of the image to use for the instance.
        my_key_id (str): The ID of the SSH key to use for the instance.
        first_subnet_id (str): The ID of the subnet to create the instance in.

    Returns:
        dict: The response from the VPC service, containing details about the created instance.

    Raises:
        ApiException: If there is an error while calling the IBM Cloud API.
        ValueError: If the `IBMCLOUD_API_KEY` environment variable is not set.
    """
    security_group_identity_model = {"id": sg_id}
    subnet_identity_model = {"id": first_subnet_id}
    primary_network_interface = {
        "name": "eth0",
        "subnet": subnet_identity_model,
        "security_groups": [security_group_identity_model],
    }
    vsi_name = f"{prefix}-tailscale-instance"
    storage_volume_name = f"{vsi_name}-boot"

    boot_volume_profile = {
        "capacity": 100,
        "name": storage_volume_name,
        "profile": {"name": "general-purpose"},
    }

    boot_volume_attachment = {
        "delete_volume_on_instance_delete": True,
        "volume": boot_volume_profile,
    }

    key_identity_model = {"id": my_key_id}
    profile_name = "bx2-2x8"
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Load and render the cloud-config template
    env = Environment(loader=FileSystemLoader(script_dir))

    template = env.get_template("cloud_config.sh")
    user_data_script = template.render(
        tailscale_api_token=tailscale_device_token, first_subnet_cidr=first_subnet_cidr
    )

    instance_prototype = {}
    instance_prototype["name"] = vsi_name
    instance_prototype["keys"] = [key_identity_model]
    instance_prototype["profile"] = {"name": profile_name}
    instance_prototype["resource_group"] = {"id": resource_group_id}
    instance_prototype["vpc"] = {"id": vpc_id}
    instance_prototype["image"] = {"id": image_id}
    instance_prototype["zone"] = {"name": zone}
    instance_prototype["boot_volume_attachment"] = boot_volume_attachment
    instance_prototype["primary_network_interface"] = primary_network_interface
    instance_prototype["user_data"] = user_data_script

    try:
        resp = vpc_client.create_instance(instance_prototype)
        return resp
    except ApiException as e:
        logging.error("API exception {}.".format(str(e)))
        quit(1)


def get_ssh_key_id(client, ssh_key):
    """
    Retrieves the ID of an SSH key by its name.

    This function uses the VPC service to list all SSH keys in the account and then
    iterates through the list to find the key with the specified name.

    Args:
        client (VpcV1): An instance of the VpcV1 service.
        ssh_key (str): The name of the SSH key to find.

    Returns:
        str: The ID of the SSH key if found, otherwise None.

    Raises:
        ApiException: If there is an error while calling the IBM Cloud API.
        ValueError: If the `IBMCLOUD_API_KEY` environment variable is not set.
    """
    keys = client.list_keys().get_result()
    for key in keys["keys"]:
        if key["name"] == ssh_key:
            return key["id"]
    return None
