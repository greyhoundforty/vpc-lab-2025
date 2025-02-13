import os
import sys
import ibm_vpc
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core import ApiException
from tamga import Tamga
import time
from time import sleep
import random
from utils import vpc_client, get_group_id_by_name
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from haikunator import Haikunator

## Use Haikunator to generate a unique heroku like base name for resources.
## Handy while testing
haikunator = Haikunator()


logger = Tamga(logToJSON=True, logToConsole=False)

region = "us-south"

ibmcloud_api_key = os.environ.get("IBMCLOUD_API_KEY")
if not ibmcloud_api_key:
    raise ValueError("IBMCLOUD_API_KEY environment variable not found")

resource_group_name = os.environ.get("RESOURCE_GROUP")
if not resource_group_name:
    raise ValueError("RESOURCE_GROUP environment variable not found")

def create_public_gateways(vpc_client, vpc_id, zone_name, resource_group_id):
    vpc_identity_model = {}
    vpc_identity_model['id'] = vpc_id

    zone_identity_model = {}
    zone_identity_model['name'] = zone_name

    resource_group_identity_model = {}
    resource_group_identity_model['id'] = resource_group_id

    vpc = vpc_identity_model
    zone = zone_identity_model
    name = f'{basename}-pgw-{zone}'
    resource_group = resource_group_identity_model
    response = vpc_client.create_public_gateway(
        vpc,
        zone,
        name=name,
        resource_group=resource_group,
    ).get_result()

    return response





    # time.sleep(random.randint(2, 8))
    # return service

def create_subnets(region):
    service = "thing"
    time.sleep(random.randint(2, 8))
    return service

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

job_progress = Progress(
    "{task.description}",
    SpinnerColumn(),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
)
job1 = job_progress.add_task(f"[green]Creating VPC in the {region} region", total=3)
job2 = job_progress.add_task("[orange]Creating Public Gateways and Subnets", total=3)
job3 = job_progress.add_task("[orange]Configuring VPC Security Groups", total=2)
job4 = job_progress.add_task("[orange]Creating Tailscale token", total=1)
job5 = job_progress.add_task("[orange]Creating Tailscale compute instance", total=1)
# job5 = job_progress.add_task("[blue]Creating Tailscale device access token")
# job6 = job_progress.add_task("[cyan]Creating Tailscale compute instance")

total = sum(task.total for task in job_progress.tasks)
overall_progress = Progress()
overall_task = overall_progress.add_task("All Jobs", total=int(total))

progress_table = Table.grid()
progress_table.add_row(
    Panel.fit(
        overall_progress, title="Overall Progress", border_style="green", padding=(2, 2)
    ),
    Panel.fit(job_progress, title="[b]Jobs", border_style="red", padding=(1, 2)),
)

with Live(progress_table, refresh_per_second=10):
    # Job 1 - create vpc client, retrieve resource group id, create vpc in the region
    vpc_client = vpc_client(ibmcloud_api_key, region)
    job_progress.update(job1, advance=1)
    resource_group_identity_model = {}
    resource_group_identity_model['id'] = get_group_id_by_name(resource_group_name)
    resource_group_id = resource_group_identity_model
    job_progress.update(job1, advance=1)
    basename = haikunator.haikunate(token_length=0, delimiter='')
    vpc_name = f'{basename}-vpc'
    address_prefix_management = 'auto'
    response = vpc_client.create_vpc(
        classic_access=False,
        address_prefix_management=address_prefix_management,
        name=vpc_name,
        resource_group=resource_group_id
    ).get_result()
    vpc_id = response['id']
    job_progress.update(job1, advance=1)

    # Job 2 = create public gateways and subnets 
    regional_zones = []
    zones = vpc_client.list_region_zones(region).get_result()['zones']
    for zone in zones:
        regional_zones.append(zone['name'])
    job_progress.update(job2, advance=1)

    for zone in regional_zones:
        create_public_gateways(vpc_client, vpc_id, zone, resource_group_id)
        job_progress.update(job2, advance=1)
        create_subnets(region)
        job_progress.update(job2, advance=1)
    # # Job 3 has 2 steps
    # create_public_gateways(region)
    # job_progress.update(job3) 
    # create_subnets(region)
    # job_progress.update(job3)

    # # Job 4 has 2 steps
    # create_security_groups(region)
    # job_progress.update(job4)
    # create_security_groups(region)
    # job_progress.update(job4)
    # # ...advance job4 again for the second step...

    # # Job 5 & Job 6 each have a single step
    # create_tailscale_token(region)
    # job_progress.update(job5)
    # create_tailscale_compute(region)
    # job_progress.update(job6)

    # Update overall progress
    completed = sum(task.completed for task in job_progress.tasks)
    overall_progress.update(overall_task, completed=completed)

    # Optionally let the user see the finished bars for a bit
    while not overall_progress.finished:
        sleep(0.1)

# with Live(progress_table, refresh_per_second=10):
#     while not overall_progress.finished:
#         sleep(0.1)
#         for job in job_progress.tasks:
#             if not job.finished:
#                 job_progress.advance(job.id)

#         completed = sum(task.completed for task in job_progress.tasks)
#         overall_progress.update(overall_task, completed=completed)



