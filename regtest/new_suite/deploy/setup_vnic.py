#!/usr/bin/python
# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import yaml

if __name__ == "__main__":
    network_config_file = os.environ["NETWORK"]
    network_config = yaml.load(open(network_config_file, "r"))
    os.system("sudo ovs-vsctl --may-exist add-port br-external \
              mgmt_vnic -- set Interface mgmt_vnic type=internal")
    os.system("sudo ip addr flush mgmt_vnic")
    os.system("sudo ip link set mgmt_vnic up")
    for sys_intf in network_config["sys_intf_mappings"]:
        if sys_intf["name"] == "mgmt" and sys_intf.get("vlan_tag"):
            os.system("sudo ovs-vsctl set port mgmt_vnic tag=%s"
                      % sys_intf["vlan_tag"])

    for net_info in network_config["ip_settings"]:
        if net_info["name"] == "mgmt":
            mgmt_ip_range_end = net_info["ip_ranges"][0][1]
            mgmt_netmask = net_info["cidr"].split('/')[1]
            os.system(r"sudo ip addr add %s/%s dev mgmt_vnic"
                      % (mgmt_ip_range_end, mgmt_netmask))
