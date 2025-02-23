import sys
import os
import pytest
import pdb
from unittest.mock import patch, MagicMock
from click.testing import CliRunner


# Add the directory containing main.py to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import main


# Mock environment variables
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("TAILSCALE_API_KEY", "mock_tailscale_api_key")
    monkeypatch.setenv("TAILNET_ID", "mock_tailnet_id")
    monkeypatch.setenv("IBMCLOUD_API_KEY", "mock_ibmcloud_api_key")


# Mock the VPC client and other functions
@pytest.fixture
def mock_vpc_client():
    with patch("main.vpc_client") as mock_client:
        # Return a mock object
        mock_client_instance = MagicMock()
        # Mock list_region_zones or whichever call returns the zones
        mock_client_instance.list_region_zones.return_value = {
            "zones": [
                {"name": "us-south-1"},
                {"name": "us-south-2"},
                {"name": "us-south-3"},
            ]
        }
        mock_client.return_value = mock_client_instance
        yield mock_client


@pytest.fixture
def mock_get_group_id_by_name():
    with patch("main.get_group_id_by_name") as mock_func:
        yield mock_func


@pytest.fixture
def mock_create_vpc():
    with patch("main.create_vpc") as mock_func:
        yield mock_func


@pytest.fixture
def mock_create_public_gateways():
    with patch("main.create_public_gateways") as mock_func:
        yield mock_func


@pytest.fixture
def mock_create_subnets():
    with patch("main.create_subnets") as mock_func:
        yield mock_func


@pytest.fixture
def mock_create_tailscale_sg_group():
    with patch("main.create_tailscale_sg_group") as mock_func:
        yield mock_func


@pytest.fixture
def mock_create_rules():
    with patch("main.create_rules") as mock_func:
        yield mock_func


@pytest.fixture
def mock_create_tailscale_key():
    with patch("main.create_tailscale_key") as mock_func:
        yield mock_func


@pytest.fixture
def mock_get_ssh_key_id():
    with patch("main.get_ssh_key_id") as mock_func:
        yield mock_func


@pytest.fixture
def mock_get_latest_ubuntu():
    with patch("main.get_latest_ubuntu") as mock_func:
        yield mock_func


@pytest.fixture
def mock_create_new_instance():
    with patch("main.create_new_instance") as mock_func:
        yield mock_func


def test_main(
    mock_vpc_client,
    mock_get_group_id_by_name,
    mock_create_vpc,
    mock_create_public_gateways,
    mock_create_subnets,
    mock_create_tailscale_sg_group,
    mock_create_rules,
    mock_create_tailscale_key,
    mock_get_ssh_key_id,
    mock_get_latest_ubuntu,
    mock_create_new_instance,
):
    # pdb.set_trace()
    # Set up mock return values
    mock_vpc_client.return_value = MagicMock()
    mock_get_group_id_by_name.return_value = "mock_resource_group_id"
    mock_create_vpc.return_value = {"id": "mock_vpc_id"}
    mock_create_public_gateways.return_value = {"id": "mock_pgw_id"}
    mock_create_subnets.return_value = {
        "id": "mock_subnet_id",
        "zone": {"name": "mock_zone"},
    }
    mock_create_tailscale_sg_group.return_value = {"id": "mock_sg_id"}
    mock_create_rules.return_value = None
    mock_create_tailscale_key.return_value = "mock_tailscale_device_token"
    mock_get_ssh_key_id.return_value = "mock_ssh_key_id"
    mock_get_latest_ubuntu.return_value = "mock_image_id"
    mock_create_new_instance.return_value = MagicMock(
        get_result=lambda: {"id": "mock_instance_id"}
    )

    # Use CliRunner to invoke the main function with command-line arguments
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--resource-group",
            "CDE",
            "--region",
            "us-south",
            "--prefix",
            "rpv3",
            "--tailscale-tag",
            "tag:rst",
            "--ssh-key",
            "mock_ssh_key",
        ],
    )

    # Print the result output for debugging
    print(result.output)

    # Check that the command executed successfully

    # Add assertions to verify the expected behavior
    mock_vpc_client.assert_called_once_with("mock_ibmcloud_api_key", "us-south")
    mock_get_group_id_by_name.assert_called_once_with("CDE")
    mock_create_vpc.assert_called_once_with(
        mock_vpc_client.return_value, "mock_resource_group_id", "rpv3"
    )
    mock_create_public_gateways.assert_called()
    mock_create_subnets.assert_called()
    mock_create_tailscale_sg_group.assert_called_once_with(
        mock_vpc_client.return_value, "mock_vpc_id", "mock_resource_group_id", "rpv3"
    )
    mock_create_rules.assert_called_once_with(
        mock_vpc_client.return_value, "mock_sg_id"
    )
    mock_create_tailscale_key.assert_called_once_with(
        "mock_tailscale_api_key", "mock_tailnet_id", "tag:rst"
    )
    mock_get_ssh_key_id.assert_called_once_with(
        mock_vpc_client.return_value, "mock_ssh_key"
    )
    mock_get_latest_ubuntu.assert_called_once_with(mock_vpc_client.return_value)
    mock_create_new_instance.assert_called_once_with(
        mock_vpc_client.return_value,
        "rpv3",
        "mock_sg_id",
        "mock_resource_group_id",
        "mock_vpc_id",
        "mock_zone",
        "mock_image_id",
        "mock_ssh_key_id",
        "mock_subnet_id",
    )

    assert result.exit_code == 0
