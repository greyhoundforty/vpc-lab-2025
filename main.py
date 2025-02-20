import os
from tamga import Tamga
import time
from time import sleep
import random
import click
from utils import *
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
    "--tailscale-tag",
    prompt="Tailscale tag to add to authentication token.",
    help="Tailscale tag",
)
# @click.option(
#     "--ssh-key",
#     prompt="Name of an existing SSH key in the region.",
#     help="VPC SSH key name",
# )
# @click.option(
#     "--dns-zone",
#     prompt="Name of the Private DNS zone to create",
#     help="DNS Zone name",
# )
# ssh_key, dns_zone
def main(resource_group, region, prefix, tailscale_tag):
    job_progress = Progress(
        "{task.description}",
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )
    job1 = job_progress.add_task(
        f"[green]Starting VPC deployment in the {region} region", total=2
    )
    job2 = job_progress.add_task("[green]Creating Public Gateways", total=1)
    job3 = job_progress.add_task("[green]Creating front and backend subnets", total=2)
    job4 = job_progress.add_task("[blue]Creating Tailscale Security Group", total=2)
    job5 = job_progress.add_task("[blue]Creating Tailscale device token", total=1)
    job6 = job_progress.add_task("[blue]Creating Tailscale compute", total=3)
    # job6 = job_progress.add_task("[yellow]Creating Private DNS Zone", total=2)
    # job7 = job_progress.add_task(
    #     "[yellow]Creating Private DNS Custom Resolver", total=2
    # )

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
        client = vpc_client(ibmcloud_api_key, region)
        resource_group_id = get_group_id_by_name(resource_group)
        job_progress.update(job1, advance=1)
        response = create_vpc(client, resource_group_id, prefix)
        vpc_id = response["id"]
        job_progress.update(job1, advance=1)

        # Job 2 = create public gateways and subnets
        regional_zones = []
        zones = client.list_region_zones(region).get_result()["zones"]
        for zone in zones:
            regional_zones.append(zone["name"])
        job_progress.update(job2, advance=1)

        all_frontend_subnets = []
        all_backend_subnets = []

        for i, zone in enumerate(regional_zones):
            pgw_response = create_public_gateways(
                client, vpc_id, zone, resource_group_id, prefix
            )
            pg_id = pgw_response["id"]
            if i == 0:  # Only create frontend subnet in the first zone
                frontend_subnet = create_subnets(
                    client, pg_id, resource_group_id, vpc_id, zone, f"{prefix}-frontend"
                )
                all_frontend_subnets.append(frontend_subnet["id"])
                job_progress.update(job3, advance=1)
            backend_subnet = create_subnets(
                client, None, resource_group_id, vpc_id, zone, f"{prefix}-backend"
            )

            all_backend_subnets.append(backend_subnet["id"])
            job_progress.update(job3, advance=1)

        first_subnet_zone = "{region}-1"

        # job 4 create secrutiy group
        ts_group_resonse = create_tailscale_sg_group(
            client, vpc_id, resource_group_id, prefix
        )
        job_progress.update(job4, advance=1)
        sg_id = ts_group_resonse["id"]
        update_rules = create_rules(client, sg_id)
        job_progress.update(job4, advance=1)
        tailscale_device_token = create_tailscale_key(
            tailscale_api_key, tailnet_id, tailscale_tag
        )
        job_progress.update(job5, advance=1)
        first_subnet_id = all_frontend_subnets[0]["id"]
        first_subnet_zone = "{region}-1"

        # first_zone_subnet_id = frontend_subnets["subnets"][0]["id"]
        # new_vnic = create_vnic(
        #     client, first_subnet_id, resource_group_id, prefix, sg_id
        # )
        job_progress.update(job6, advance=1)
        logger.info(f"VNIC ID: {new_vnic['id']}")
        image_id = get_latest_ubuntu(client)
        logger.info(f"Ubuntu Image ID: {image_id}")
        job_progress.update(job6, advance=1)

        my_key_id = "r038-441f040d-e836-4d5f-ad3f-8ea475652ce2"

        new_instance = create_new_instance(
            client,
            prefix,
            sg_id,
            resource_group_id,
            vpc_id,
            first_subnet_zone,
            image_id,
            my_key_id,
            first_subnet_id,
        )
        job_progress.update(job6, advance=1)
        logger.info(f"New Instance ID: {new_instance['id']}")
        completed = sum(task.completed for task in job_progress.tasks)
        overall_progress.update(overall_task, completed=completed)

        while not overall_progress.finished:
            sleep(0.1)


if __name__ == "__main__":
    main()
