#!/bin/bash
set -x
set -e
iface_name=${1:-"tun0"}
vpn_service_name=${2:-"client.service"}
ifconfig "$iface_name" || start_vpn="yes"
if [ "$start_vpn" = "yes" ]
then
  echo "Starting VPN"
  openvpn --config /home/jitu/.openvpn/config.ovpn &
else
  echo "VPN already started"
fi
