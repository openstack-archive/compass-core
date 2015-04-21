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

"""Ansible playbook callback after a playbook run has completed."""
import logging
import os
import simplejson as json
import sys

current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_dir + '/..')

import switch_virtualenv

from compass.apiclient.restful import Client
from compass.utils import flags

flags.add('compass_server',
          help='compass server url',
          default='http://127.0.0.1/api')
flags.add('compass_user_email',
          help='compass user email',
          default='admin@huawei.com')
flags.add('compass_user_password',
          help='compass user password',
          default='admin')


class CallbackModule(object):
    def __init__(self):
        self.disabled = False
        try:
            self.client = self._get_client()
        except Exception:
            self.disabled = True
            logging.error("No compass server found"
                          "disabling this plugin")

    def _get_client(self):
        return Client(flags.OPTIONS.compass_server)

    def _login(self, client):
        """get apiclient token."""
        status, resp = client.get_token(
            flags.OPTIONS.compass_user_email,
            flags.OPTIONS.compass_user_password
        )
        logging.info(
            'login status: %s, resp: %s',
            status, resp
        )
        if status >= 400:
            raise Exception(
                'failed to login %s with user %s',
                flags.OPTIONS.compass_server,
                flags.OPTIONS.compass_user_email
            )
        return resp['token']

    def playbook_on_stats(self, stats):
        hosts = sorted(stats.processed.keys())
        host_vars = self.playbook.inventory.get_variables(hosts[0])
        cluster_name = host_vars['cluster_name']

        failures = False
        unreachable = False

        for host in hosts:
            summary = stats.summarize(host)

            if summary['failures'] > 0:
                failures = True
            if summary['unreachable'] > 0:
                unreachable = True

        if failures or unreachable:
            return

        self._login(self.client)

        for host in hosts:
            clusterhost_name = host + "." + cluster_name
            self.client.clusterhost_ready(clusterhost_name)
