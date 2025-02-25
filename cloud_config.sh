#!/bin/bash
set -o errexit
set -o nounset
set -o pipefail

DEBIAN_FRONTEND=noninteractive apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-pip curl wget unzip jq build-essential

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
echo 'net.ipv4.ip_forward = 1' | tee -a /etc/sysctl.d/99-tailscale.conf
echo 'net.ipv6.conf.all.forwarding = 1' | tee -a /etc/sysctl.d/99-tailscale.conf
sysctl -p /etc/sysctl.d/99-tailscale.conf
tailscale up --advertise-routes={{ first_subnet_cidr }} --authkey={{ tailscale_api_token }} --accept-routes

cat <<EOF > /etc/networkd-dispatcher/routable.d/50-tailscale
#!/bin/sh
nethtool -K %s rx-udp-gro-forwarding on rx-gro-list off \n' "$(ip -o route get 8.8.8.8 | cut -f 5 -d " ")"
EOF

chmod 755 /etc/networkd-dispatcher/routable.d/50-tailscale

# Install Docker
