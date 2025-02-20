import os
from tamga import Tamga
import time
from time import sleep
import random
import click
from utils import vpc_client, get_group_id_by_name, create_vpc
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table

# add in dotenv
# tailscale api key
# tailscale tailnet id
# ibmcloud api key

logger = Tamga(logToJSON=True, logToConsole=False)


tailscale_api_key = os.getenv("TAILSCALE_API_KEY")
if not tailscale_api_key:
    logger.error("TAILSCALE_API_KEY is not set")
    exit(1)

tailnet_id = os.getenv("TAILNET_ID")
if not tailnet_id:
    logger.error("TAILNET_ID is not set")
    exit(1)

ibmcloud_api_key = os.environ.get("IBMCLOUD_API_KEY")
if not ibmcloud_api_key:
    logger.error("IBMCLOUD_API_KEY environment variable not found")


@click.command()
@click.option(
    "--resource-group",
    prompt="Enter the IBM Cloud resource group name",
    help="IBM Cloud resource group",
)
@click.option(
    "--region",
    prompt="Enter the IBM Cloud region to deploy the VPC",
    help="IBM Cloud region",
)
@click.option(
    "--prefix",
    prompt="Enter a prefix for the VPC resources",
    help="Prefix for the VPC resources",
)
@click.option(
    "--ssh-key",
    prompt="Name of an existing SSH key in the region.",
    help="VPC SSH key name",
)
@click.option(
    "--dns-zone",
    prompt="Name of the Private DNS zone to create",
    help="DNS Zone name",
)
def main(resource_group, region, prefix, ssh_key, dns_zone):
    job_progress = Progress(
        "{task.description}",
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )
    job1 = job_progress.add_task(
        f"[green]Starting VPC deployment in the {region} region", total=3
    )
    job2 = job_progress.add_task(
        "[orange]Creating Public Gateways and Subnets", total=3
    )
    job3 = job_progress.add_task("[orange]Configuring VPC Security Groups", total=2)
    job4 = job_progress.add_task("[blue]Creating Tailscale token", total=1)
    job5 = job_progress.add_task("[blue]Creating Tailscale compute instance", total=1)
    job6 = job_progress.add_task("[yellow]Creating Private DNS Zone", total=2)
    job7 = job_progress.add_task(
        "[yellow]Creating Private DNS Custom Resolver", total=2
    )

    total = sum(task.total for task in job_progress.tasks)
    overall_progress = Progress()
    overall_task = overall_progress.add_task("All Jobs", total=int(total))

    progress_table = Table.grid()
    progress_table.add_row(
        Panel.fit(
            overall_progress,
            title="Overall Progress",
            border_style="green",
            padding=(2, 2),
        ),
        Panel.fit(job_progress, title="[b]Jobs", border_style="red", padding=(1, 2)),
    )

    with Live(progress_table, refresh_per_second=10):
        # Job 1 - create vpc client, retrieve resource group id, create vpc in the region
        vpc_client = vpc_client(ibmcloud_api_key, region)
        job_progress.update(job1, advance=1)

        job_progress.update(job1, advance=1)

        vpc_id = response["id"]
        job_progress.update(job1, advance=1)

        # Job 2 = create public gateways and subnets
        regional_zones = []
        zones = vpc_client.list_region_zones(region).get_result()["zones"]
        for zone in zones:
            regional_zones.append(zone["name"])
        job_progress.update(job2, advance=1)

        for zone in regional_zones:
            create_public_gateways(vpc_client, vpc_id, zone, resource_group_id)
            job_progress.update(job2, advance=1)
            create_subnets(vpc_client, vpc_id, zone, resource_group_id)
            job_progress.update(job2, advance=1)

        completed = sum(task.completed for task in job_progress.tasks)
        overall_progress.update(overall_task, completed=completed)

        while not overall_progress.finished:
            sleep(0.1)
