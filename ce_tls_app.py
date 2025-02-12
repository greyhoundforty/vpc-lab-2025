import os
import subprocess
import click
import tldextract
from datetime import datetime
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core import ApiException
from ibm_code_engine_sdk.code_engine_v2 import CodeEngineV2, ProjectsPager
from tamga import Tamga
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

logger = Tamga(logToJSON=True, logToConsole=True)

ibmcloud_api_key = os.environ.get("IBMCLOUD_API_KEY")
if not ibmcloud_api_key:
    raise ValueError("IBMCLOUD_API_KEY environment variable not found")


def code_engine_client(region):
    """
    Create a Code Engine client in the specified IBM Cloud region.
    See https://cloud.ibm.com/apidocs/codeengine/v2?code=python#endpointurls
    """
    authenticator = IAMAuthenticator(apikey=ibmcloud_api_key)
    ce_client = CodeEngineV2(authenticator=authenticator)
    ce_client.set_service_url("https://api." + region + ".codeengine.cloud.ibm.com/v2")
    return ce_client


def generate_tls_certificate(custom_domain, dns_provider, certbot_email):
    """
    Generate a TLS certificate for the custom domain using certbot and DNS challenge.
    """
    cert_dir = f"certbot-output"
    os.makedirs(cert_dir, exist_ok=True)

    # Generate private key
    private_key_path = os.path.join(cert_dir, "private-key.pem")
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "RSA", "-out", private_key_path],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Generate CSR
    csr_path = os.path.join(cert_dir, "csr.pem")
    subprocess.run(
        [
            "openssl",
            "req",
            "-new",
            "-key",
            private_key_path,
            "-out",
            csr_path,
            "-subj",
            f"/CN={custom_domain}",
        ],
        check=True,
    )

    certbot_cmd = [
        "certbot",
        "certonly",
        "-a",
        "dns-multi",
        "--dns-multi-credentials",
        "./dns-multi.ini",
        "--csr",
        csr_path,
        "--cert-path",
        os.path.join(cert_dir, "cert.pem"),
        "--fullchain-path",
        os.path.join(cert_dir, "fullchain.pem"),
        "-d",
        custom_domain,
        "--non-interactive",
        "--agree-tos",
        "-m",
        certbot_email,
        "--config-dir",
        cert_dir,
        "--work-dir",
        cert_dir,
        "--logs-dir",
        cert_dir,
    ]

    with open("dns-multi.ini", "w") as f:
        f.write(f"dns_multi_provider = {dns_provider}\n")

    os.chmod("dns-multi.ini", 0o600)

    # subprocess.run(certbot_cmd, check=True)
    subprocess.run(
        certbot_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    cert_path = f"{cert_dir}/fullchain.pem"
    key_path = f"{cert_dir}/private-key.pem"

    with open(cert_path, "r") as cert_file:
        tls_cert = cert_file.read()

    with open(key_path, "r") as key_file:
        tls_key = key_file.read()

    logger.success("Certificate generation successful!")

    return tls_cert, tls_key


def get_project_id(ce_client, project_name):
    """
    Get the Code Engine project ID from the project name.
    Used by custom_domain mapping function
    """
    all_results = []
    pager = ProjectsPager(
        client=ce_client,
        limit=100,
    )
    while pager.has_next():
        next_page = pager.get_next()
        assert next_page is not None
        all_results.extend(next_page)
    for project in all_results:
        if project["name"] == project_name:
            return project["id"]
    raise Exception(f"Project with name {project_name} not found.")


def create_code_engine_secret(ce_client, project_id, secret_name, tls_cert, tls_key):
    """
    Create a secret in the specified Code Engine project.
    """
    secret_data = {
        "tls.crt": tls_cert,
        "tls.key": tls_key,
    }

    response = ce_client.create_secret(
        project_id=project_id, format="tls", name=secret_name, data=secret_data
    ).get_result()

    return response["id"]


# def update_dns(custom_domain, code_engine_cname):
#     """
#     We need to get the canonical domain name from the custom_domain.
#     This is required to update the DNS records in Digital Ocean.
#     """

#     extracted = tldextract.extract(custom_domain)
#     canonical_domain = extracted.domain + "." + extracted.suffix
#     client = digitalocean_client()
#     if not code_engine_cname.endswith("."):
#         code_engine_cname += "."
#     body = {"type": "CNAME", "name": extracted.subdomain, "data": code_engine_cname}
#     try:
#         logger.info(
#             f"Starting DNS update for {custom_domain} to point to {code_engine_cname}"
#         )
#         client.domains.create_record(canonical_domain, body=body)
#     except ApiException as e:
#         logger.error(
#             f"Error updating DNS for {custom_domain} to point to {code_engine_cname}"
#         )
#         raise e


def list_domain_mappings(ce_client, app_name, project_id):
    """
    List the custom domain mappings for the Code Engine application.
    """
    response = ce_client.list_domain_mappings(project_id=project_id)
    domain_mappings = response.get_result()
    # Filter domain mappings to only include those with visibility = 'custom' and matching app_name
    custom_domain_mappings = [
        mapping
        for mapping in domain_mappings["domain_mappings"]
        if mapping["visibility"] == "custom"
        and mapping["component"]["name"] == app_name
    ]
    if not custom_domain_mappings:
        logger.info(f"No custom domain mappings found for app: {app_name}")
        return None
    custom_domain_name = custom_domain_mappings[0]["name"]
    return custom_domain_name


def map_custom_domain(ce_client, app_name, project_id, custom_domain, secret_name):
    component_ref_model = {
        "name": app_name,
        "resource_type": "app_v2",
    }
    response = ce_client.create_domain_mapping(
        project_id=project_id,
        component=component_ref_model,
        name=custom_domain,
        tls_secret=secret_name,
    )
    domain_mapping = response.get_result()
    return domain_mapping


@click.command()
@click.option("--region", prompt="Enter the IBM Cloud region", help="IBM Cloud region")
@click.option(
    "--project-name",
    prompt="Enter the IBM Cloud Code Engine project name",
    help="IBM Cloud Code Engine project name",
)
@click.option(
    "--app-name",
    prompt="Enter the IBM Cloud Code Engine application name",
    help="IBM Cloud Code Engine app name",
)
@click.option("--custom-domain", prompt="Enter the custom domain", help="Custom domain")
@click.option(
    "--dns-provider",
    prompt="Enter your DNS provider plugin name",
    help="DNS provider plugin name",
)
# @click.option("--dns-token", prompt="Enter your DNS provider token", help="DNS provider token")
@click.option(
    "--certbot-email",
    prompt="Enter your email address for certbot request",
    help="Email address for certbot request",
)
# def main(region, project_name, app_name, custom_domain, certbot_email):
def main(certbot_email, custom_domain, region, app_name, project_name, dns_provider):
    """
    This script automates the process of mapping a custom domain to an IBM Cloud Code Engine application.
    """

    with Progress(
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        expand=True,
    ) as progress:
        overall_task = progress.add_task("Overall progress", total=5)

        # Step 1: Pull code engine project ID
        progress.console.log("[bold]Step 1:[/bold] Pulling CE project id from name...")
        ce_client = code_engine_client(region)
        project_id = get_project_id(ce_client, project_name)
        logger.info(f"Working on Project ID: {project_id}")
        progress.update(overall_task, advance=1)

        # Step 2: Pull application ID
        progress.console.log(
            "[bold]Step 2:[/bold] Pulling application id from project..."
        )
        response = ce_client.get_app(project_id=project_id, name=app_name)
        app = response.get_result()
        code_engine_app_endpoint = app.get("endpoint")
        logger.info(f"Current Code Engine App Endpoint: {code_engine_app_endpoint}")
        progress.update(overall_task, advance=1)

        # Step 3: Generate TLS certificate
        progress.console.log("[bold]Step 3:[/bold] Generating TLS certificate...")
        tls_cert, tls_key = generate_tls_certificate(
            custom_domain, dns_provider, certbot_email
        )
        logger.success("TLS certificate generated successfully.")
        progress.update(overall_task, advance=1)

        # Step 4: Remove existing custom domain mapping
        progress.console.log(
            "[bold]Step 4:[/bold] Checking/removing existing domain mapping..."
        )
        current_domain_mapping = list_domain_mappings(ce_client, app_name, project_id)
        if current_domain_mapping:
            ce_client.delete_domain_mapping(
                project_id=project_id, name=current_domain_mapping
            )
            logger.success(f"Removed existing domain mapping: {current_domain_mapping}")
        progress.update(overall_task, advance=1)

        # Step 5: Map custom domain to Code Engine project
        progress.console.log("[bold]Step 5:[/bold] Mapping custom domain to project...")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        secret_name = f"tls-secret-{timestamp}-{app_name}"
        create_code_engine_secret(ce_client, project_id, secret_name, tls_cert, tls_key)
        map_custom_domain(ce_client, app_name, project_id, custom_domain, secret_name)
        logger.success(f"Custom domain {custom_domain} mapped successfully.")
        progress.update(overall_task, advance=1)

    logger.success("All steps completed successfully.")


if __name__ == "__main__":
    main()
