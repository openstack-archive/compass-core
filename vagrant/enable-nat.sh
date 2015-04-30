#!/bin/bash

sudo echo 1 > /proc/sys/net/ipv4/ip_forward
sudo iptables -F
sudo iptables -t nat -F
sudo iptables -t mangle -F
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo iptables -A FORWARD -i eth1 -j ACCEPT
