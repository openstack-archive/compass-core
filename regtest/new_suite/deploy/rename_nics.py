#!/usr/bin/env python
#
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
import sys
import yaml


def exec_cmd(cmd):
    print cmd
    os.system(cmd)


def rename_nics(dha_info, rsa_file, compass_ip):
    for host in dha_info['hosts']:
        host_name = host['name']
        interfaces = host.get('interfaces')
        if interfaces:
            for interface in interfaces:
                nic_name = interfaces.keys()[0]
                mac = interfaces.values()[0]

                exec_cmd("ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                          -i %s root@%s \
                          'cobbler system edit --name=%s \
                          --interface=%s --mac=%s'"
                         % (rsa_file, compass_ip, host_name, nic_name, mac))

    exec_cmd("ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
              -i %s root@%s \
              'cobbler sync'" % (rsa_file, compass_ip))

if __name__ == "__main__":
    assert(len(sys.argv) == 4)
    rename_nics(yaml.load(open(sys.argv[1])), sys.argv[2], sys.argv[3])
