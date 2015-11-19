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

"""Compass api client library.
"""

import json
import logging
import requests

class Client(object):
    """compass restful api wrapper"""

    def __init__(self, url, headers=None, proxies=None, stream=None):
        logging.info('create api client %s', url)
        self.url_ = url
        self.session_ = requests.Session()

        if headers:
            self.session_.headers.update(headers)
        self.session_.headers.update({
            'Accept': 'application/json'
        })

        if proxies is not None:
            self.session_.proxies = proxies

        if stream is not None:
            self.session_.stream = stream

    def __del__(self):
        self.session_.close()

    @classmethod
    def _get_response(cls, resp):
        response_object = {}
        try:
            response_object = resp.json()
        except Exception as error:
            logging.error('failed to load object from %s: %s',
                          resp.url, resp.content)
            logging.exception(error)
            response_object['status'] = 'Json Parsing Failed'
            response_object['message'] = resp.content

        return resp.status_code, response_object

    def _get(self, req_url, data=None):
        url = '%s%s' % (self.url_, req_url)
        logging.debug('get %s with data %s', url, data)
        if data:
            resp = self.session_.get(url, params=data)
        else:
            resp = self.session_.get(url)

        return self._get_response(resp)

    def _post(self, req_url, data=None):
        url = '%s%s' % (self.url_, req_url)
        logging.debug('post %s with data %s', url, data)
        if data:
            resp = self.session_.post(url, json.dumps(data))
        else:
            resp = self.session_.post(url)

        return self._get_response(resp)

    def _put(self, req_url, data=None):
        """encapsulate put method."""
        url = '%s%s' % (self.url_, req_url)
        logging.debug('put %s with data %s', url, data)
        if data:
            resp = self.session_.put(url, json.dumps(data))
        else:
            resp = self.session_.put(url)

        return self._get_response(resp)

    def _patch(self, req_url, data=None):
        url = '%s%s' % (self.url_, req_url)
        logging.debug('patch %s with data %s', url, data)
        if data:
            resp = self.session_.patch(url, json.dumps(data))
        else:
            resp = self.session_.patch(url)

        return self._get_response(resp)

    def _delete(self, req_url):
        url = '%s%s' % (self.url_, req_url)
        logging.debug('delete %s', url)
        return self._get_response(self.session_.delete(url))

    def login(self, email, password):
        credential = {}
        credential['email'] = email
        credential['password'] = password
        return self._post('/users/login', data=credential)

    def get_token(self, email, password):
        credential = {}
        credential['email'] = email
        credential['password'] = password
        status, resp = self._post('/users/token', data=credential)
        if status < 400:
            self.session_.headers.update({'X-Auth-Token': resp['token']})
        return status, resp

    def get_users(self):
        users = self._get('/users')
        return users

    def list_switches(
            self,
            switch_ips=None,
            switch_ip_networks=None):
        """list switches."""
        params = {}
        if switch_ips:
            params['switchIp'] = switch_ips

        if switch_ip_networks:
            params['switchIpNetwork'] = switch_ip_networks

        switchlist = self._get('/switches', data=params)
        return switchlist

    def get_switch(self, switch_id):
        return self._get('/switches/%s' % switch_id)

    def add_switch(
            self,
            switch_ip,
            version=None,
            community=None,
            raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            data['ip'] = switch_ip
            data['credentials'] = {}
            if version:
                data['credentials']['version'] = version

            if community:
                data['credentials']['community'] = community

        return self._post('/switches', data=data)

    def update_switch(self, switch_id, state='initialized',
                      version='2c', community='public', raw_data={}):
        data = {}
        if raw_data:
            data = raw_data

        else:
            data['credentials'] = {}
            if version:
                data['credentials']['version'] = version

            if community:
                data['credentials']['community'] = community

            if state:
                data['state'] = state

        return self._put('/switches/%s' % switch_id, data=data)

    def delete_switch(self, switch_id):
        return self._delete('/switches/%s' % switch_id)

    def list_switch_machines(self, switch_id, port=None, vlans=None,
                             tag=None, location=None):
        data = {}
        if port:
            data['port'] = port

        if vlans:
            data['vlans'] = vlans

        if tag:
            data['tag'] = tag

        if location:
            data['location'] = location

        return self._get('/switches/%s/machines' % switch_id, data=data)

    def get_switch_machine(self, switch_id, machine_id):
        return self._get('/switches/%s/machines/%s' % (switch_id, machine_id))

    def list_switch_machines_hosts(self, switch_id, port=None, vlans=None,
                                   mac=None, tag=None, location=None,
                                   os_name=None, os_id=None):

        data = {}
        if port:
            data['port'] = port

        if vlans:
            data['vlans'] = vlans

        if mac:
            data['mac'] = mac

        if tag:
            data['tag'] = tag

        if location:
            data['location'] = location

        if os_name:
            data['os_name'] = os_name

        if os_id:
            data['os_id'] = os_id

        return self._get('/switches/%s/machines-hosts' % switch_id, data=data)

    def add_switch_machine(self, switch_id, mac=None, port=None,
                           vlans=None, ipmi_credentials=None,
                           tag=None, location=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if mac:
                data['mac'] = mac

            if port:
                data['port'] = port

            if vlans:
                data['vlans'] = vlans

            if ipmi_credentials:
                data['ipmi_credentials'] = ipmi_credentials

            if tag:
                data['tag'] = tag

            if location:
                data['location'] = location

        return self._post('/switches/%s/machines' % switch_id, data=data)

    def update_switch_machine(self, switch_id, machine_id, port=None,
                              vlans=None, ipmi_credentials=None, tag=None,
                              location=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if port:
                data['port'] = port

            if vlans:
                data['vlans'] = vlans

            if ipmi_credentials:
                data['ipmi_credentials'] = ipmi_credentials

            if tag:
                data['tag'] = tag

            if location:
                data['location'] = location

        return self._put('/switches/%s/machines/%s' %
                         (switch_id, machine_id), data=data)

    def delete_switch_machine(self, switch_id, machine_id):
        return self._delete('/switches/%s/machines/%s' %
                            (switch_id, machine_id))

    # test these
    def poll_switch(self, switch_id):
        data = {}
        data['find_machines'] = None
        return self._post('/switches/%s/action' % switch_id, data=data)

    def add_group_switch_machines(self, switch_id, group_machine_ids):
        data = {}
        data['add_machines'] = group_machine_ids
        return self._post('/switches/%s/action' % switch_id, data=data)

    def remove_group_switch_machines(self, switch_id, group_machine_ids):
        data = {}
        data['remove_machines'] = group_machine_ids
        return self._post('/switches/%s/action' % switch_id, data=data)

    def update_group_switch_machines(self, switch_id, group_machines):
        data = {}
        data['set_machines'] = group_machines
        return self._post('/switches/%s/action' % switch_id, data=data)
    # end

    def list_switchmachines(self, switch_ip_int=None, port=None, vlans=None,
                            mac=None, tag=None, location=None):
        data = {}
        if switch_ip_int:
            data['switch_ip_int'] = switch_ip_int

        if port:
            data['port'] = port

        if vlans:
            data['vlans'] = vlans

        if mac:
            data['mac'] = mac

        if tag:
            data['tag'] = tag

        if location:
            data['location'] = location

        return self._get('/switch-machines', data=data)

    def list_switchmachines_hosts(self, switch_ip_int=None, port=None,
                                  vlans=None, mac=None, tag=None,
                                  location=None, os_name=None, os_id=None):

        data = {}
        if switch_ip_int:
            data['switch_ip_int'] = switch_ip_int

        if port:
            data['port'] = port

        if vlans:
            data['vlans'] = vlans

        if mac:
            data['mac'] = mac

        if tag:
            data['tag'] = tag

        if location:
            data['location'] = location

        if os_name:
            data['os_name'] = os_name

        if os_id:
            data['os_id'] = os_id

        return self._get('/switches-machines-hosts', data=data)

    def show_switchmachine(self, switchmachine_id):
        return self._get('/switch-machines/%s' % switchmachine_id)

    def update_switchmachine(self, switchmachine_id,
                             port=None, vlans=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if port:
                data['port'] = port

            if vlans:
                data['vlans'] = vlans

        return self._put('/switch-machines/%s' % switchmachine_id, data=data)

    def patch_switchmachine(self, switchmachine_id,
                            vlans=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        elif vlans:
            data['vlans'] = vlans

        return self._patch('/switch-machines/%s' % switchmachine_id, data=data)

    def delete_switchmachine(self, switchmachine_id):
        return self._delete('/switch-machines/%s' % switchmachine_id)

    def list_machines(self, mac=None, tag=None, location=None):
        data = {}
        if mac:
            data['mac'] = mac

        if tag:
            data['tag'] = tag

        if location:
            data['location'] = location

        return self._get('/machines', data=data)

    def get_machine(self, machine_id):
        data = {}
        if id:
            data['id'] = id

        return self._get('/machines/%s' % machine_id, data=data)

    def update_machine(self, machine_id, ipmi_credentials=None, tag=None,
                       location=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if ipmi_credentials:
                data['ipmi_credentials'] = ipmi_credentials

            if tag:
                data['tag'] = tag

            if location:
                data['location'] = location

        return self._put('/machines/%s' % machine_id, data=data)

    def patch_machine(self, machine_id, ipmi_credentials=None,
                      tag=None, location=None,
                      raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if ipmi_credentials:
                data['ipmi_credentials'] = ipmi_credentials

            if tag:
                data['tag'] = tag

            if location:
                data['location'] = location

        return self._patch('/machines/%s' % machine_id, data=data)

    def delete_machine(self, machine_id):
        return self._delete('machines/%s' % machine_id)

    def list_subnets(self, subnet=None, name=None):
        data = {}
        if subnet:
            data['subnet'] = subnet

        if name:
            data['name'] = name

        return self._get('/subnets', data=data)

    def get_subnet(self, subnet_id):
        return self._get('/subnets/%s' % subnet_id)

    def add_subnet(self, subnet, name=None, raw_data=None):
        data = {}
        data['subnet'] = subnet
        if raw_data:
            data.update(raw_data)
        else:
            if name:
                data['name'] = name

        return self._post('/subnets', data=data)

    def update_subnet(self, subnet_id, subnet=None,
                      name=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if subnet:
                data['subnet'] = subnet

            if name:
                data['name'] = name

        return self._put('/subnets/%s' % subnet_id, data=data)

    def delete_subnet(self, subnet_id):
        return self._delete('/subnets/%s' % subnet_id)

    def list_adapters(self, name=None, distributed_system_name=None,
                      os_installer_name=None, package_installer_name=None):
        data = {}
        if name:
            data['name'] = name

        if distributed_system_name:
            data['distributed_system_name'] = distributed_system_name

        if os_installer_name:
            data['os_installer_name'] = os_installer_name

        if package_installer_name:
            data['package_installer_name'] = package_installer_name

        return self._get('/adapters', data=data)

    def get_adapter(self, adapter_id):
        return self._get('/adapters/%s' % adapter_id)

    def get_adapter_roles(self, adapter_id):
        return self._get('/adapters/%s/roles' % adapter_id)

    def get_adapter_metadata(self, adapter_id):
        return self._get('/adapters/%s/metadata' % adapter_id)

    def get_os_metadata(self, os_id):
        return self._get('/oses/%s/metadata' % os_id)

    def list_clusters(self, name=None, os_name=None,
                      distributed_system_name=None, owner=None,
                      adapter_id=None):
        data = {}
        if name:
            data['name'] = name

        if os_name:
            data['os_name'] = os_name

        if distributed_system_name:
            data['distributed_system_name'] = distributed_system_name

        if owner:
            data['owner'] = owner

        if adapter_id:
            data['adapter_id'] = adapter_id

        return self._get('/clusters', data=data)

    def get_cluster(self, cluster_id):
        return self._get('/clusters/%s' % cluster_id)

    def add_cluster(self, name, adapter_id, os_id,
                    flavor_id=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if flavor_id:
                data['flavor_id'] = flavor_id
            data['name'] = name
            data['adapter_id'] = adapter_id
            data['os_id'] = os_id

        return self._post('/clusters', data=data)

    def update_cluster(self, cluster_id, name=None,
                       reinstall_distributed_system=None,
                       raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if name:
                data['name'] = name

            if reinstall_distributed_system:
                data['reinstall_distributed_system'] = (
                    reinstall_distributed_system
                )
        return self._put('/clusters/%s' % cluster_id, data=data)

    def delete_cluster(self, cluster_id):
        return self._delete('/clusters/%s' % cluster_id)

    def get_cluster_config(self, cluster_id):
        return self._get('/clusters/%s/config' % cluster_id)

    def get_cluster_metadata(self, cluster_id):
        return self._get('/clusters/%s/metadata' % cluster_id)

    def update_cluster_config(self, cluster_id, os_config=None,
                              package_config=None, config_step=None,
                              raw_data=None):
        data = {}
        if raw_data:
            data = raw_data

        if os_config:
            data['os_config'] = os_config

        if package_config:
            data['package_config'] = package_config

        if config_step:
            data['config_step'] = config_step

        return self._put('/clusters/%s/config' % cluster_id, data=data)

    def patch_cluster_config(self, cluster_id, os_config=None,
                             package_config=None, config_step=None,
                             raw_data=None):
        data = {}
        if raw_data:
            data = raw_data

        if os_config:
            data['os_config'] = os_config

        if package_config:
            data['package_config'] = package_config

        if config_step:
            data['config_step'] = config_step

        return self._patch('/clusters/%s/config' % cluster_id, data=data)

    def delete_cluster_config(self, cluster_id):
        return self._delete('/clusters/%s/config' % cluster_id)

    # test these
    def add_hosts_to_cluster(self, cluster_id, hosts):
        data = {}
        data['add_hosts'] = hosts
        return self._post('/clusters/%s/action' % cluster_id, data=data)

    def set_hosts_in_cluster(self, cluster_id, hosts):
        data = {}
        data['set_hosts'] = hosts
        return self._post('/clusters/%s/action' % cluster_id, data=data)

    def remove_hosts_from_cluster(self, cluster_id, hosts):
        data = {}
        data['remove_hosts'] = hosts
        return self._post('/clusters/%s/action' % cluster_id, data=data)

    def review_cluster(self, cluster_id, review={}):
        data = {}
        data['review'] = review
        return self._post('/clusters/%s/action' % cluster_id, data=data)

    def deploy_cluster(self, cluster_id, deploy={}):
        data = {}
        data['deploy'] = deploy
        return self._post('/clusters/%s/action' % cluster_id, data=data)

    def get_cluster_state(self, cluster_id):
        return self._get('/clusters/%s/state' % cluster_id)

    def list_cluster_hosts(self, cluster_id):
        return self._get('/clusters/%s/hosts' % cluster_id)

    def list_clusterhosts(self):
        return self._get('/clusterhosts')

    def get_cluster_host(self, cluster_id, host_id):
        return self._get('/clusters/%s/hosts/%s' % (cluster_id, host_id))

    def get_clusterhost(self, clusterhost_id):
        return self._get('/clusterhosts/%s' % clusterhost_id)

    def add_cluster_host(self, cluster_id, machine_id=None, name=None,
                         reinstall_os=None, raw_data=None):
        data = {}
        data['machine_id'] = machine_id
        if raw_data:
            data.update(raw_data)
        else:
            if name:
                data['name'] = name

            if reinstall_os:
                data['reinstall_os'] = reinstall_os

        return self._post('/clusters/%s/hosts' % cluster_id, data=data)

    def delete_cluster_host(self, cluster_id, host_id):
        return self._delete('/clusters/%s/hosts/%s' %
                            (cluster_id, host_id))

    def delete_clusterhost(self, clusterhost_id):
        return self._delete('/clusterhosts/%s' % clusterhost_id)

    def get_cluster_host_config(self, cluster_id, host_id):
        return self._get('/clusters/%s/hosts/%s/config' %
                         (cluster_id, host_id))

    def get_clusterhost_config(self, clusterhost_id):
        return self._get('/clusterhosts/%s/config' % clusterhost_id)

    def update_cluster_host_config(self, cluster_id, host_id,
                                   os_config=None,
                                   package_config=None,
                                   raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if os_config:
                data['os_config'] = os_config

            if package_config:
                data['package_config'] = package_config

        return self._put('/clusters/%s/hosts/%s/config' %
                         (cluster_id, host_id), data=data)

    def update_clusterhost_config(self, clusterhost_id, os_config=None,
                                  package_config=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data

        else:
            if os_config:
                data['os_config'] = os_config

            if package_config:
                data['package_config'] = package_config

        return self._put('/clusterhosts/%s/config' % clusterhost_id,
                         data=data)

    def patch_cluster_host_config(self, cluster_id, host_id,
                                  os_config=None,
                                  package_config=None,
                                  raw_data=None):
        data = {}
        if raw_data:
            data = raw_data

        else:
            if os_config:
                data['os_config'] = os_config

            if package_config:
                data['package_config'] = package_config

        return self._patch('/clusters/%s/hosts/%s/config' %
                           (cluster_id, host_id), data=data)

    def patch_clusterhost_config(self, clusterhost_id, os_config=None,
                                 package_config=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data

        else:
            if os_config:
                data['os_config'] = os_config

            if package_config:
                data['package_config'] = package_config

        return self._patch('/clusterhosts/%s' % clusterhost_id, data=data)

    def delete_cluster_host_config(self, cluster_id, host_id):
        return self._delete('/clusters/%s/hosts/%s/config' %
                            (cluster_id, host_id))

    def delete_clusterhost_config(self, clusterhost_id):
        return self._delete('/clusterhosts/%s/config' % clusterhost_id)

    def get_cluster_host_state(self, cluster_id, host_id):
        return self._get('/clusters/%s/hosts/%s/state' %
                         (cluster_id, host_id))

    def update_cluster_host(self, cluster_id, host_id,
                            roles=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if roles:
                data['roles'] = roles

        return self._put('/clusters/%s/hosts/%s' %
                         (cluster_id, host_id), data=data)

    def update_clusterhost(self, clusterhost_id,
                           roles=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if roles:
                data['roles'] = roles

        return self._put('/clusterhosts/%s' % clusterhost_id, data=data)

    def patch_cluster_host(self, cluster_id, host_id,
                           roles=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if roles:
                data['roles'] = roles

        return self._patch('/clusters/%s/hosts/%s' %
                           (cluster_id, host_id), data=data)

    def patch_clusterhost(self, clusterhost_id,
                          roles=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if roles:
                data['roles'] = roles

        return self._patch('/clusterhosts/%s' % clusterhost_id, data=data)

    def get_clusterhost_state(self, clusterhost_id):
        return self._get('/clusterhosts/%s/state' % clusterhost_id)

    def update_cluster_host_state(self, cluster_id, host_id, state=None,
                                  percentage=None, message=None,
                                  raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if state:
                data['state'] = state

            if percentage:
                data['percentage'] = percentage

            if message:
                data['message'] = message

        return self._put('/clusters/%s/hosts/%s/state' % (cluster_id, host_id),
                         data=data)

    def update_clusterhost_state(self, clusterhost_id, state=None,
                                 percentage=None, message=None,
                                 raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if state:
                data['state'] = state

            if percentage:
                data['percentage'] = percentage

            if message:
                data['message'] = message

        return self._put('/clusterhosts/%s/state' % clusterhost_id, data=data)

    def list_hosts(self, name=None, os_name=None, owner=None, mac=None):
        data = {}
        if name:
            data['name'] = name

        if os_name:
            data['os_name'] = os_name

        if owner:
            data['owner'] = owner

        if mac:
            data['mac'] = mac

        return self._get('/hosts', data=data)

    def get_host(self, host_id):
        return self._get('/hosts/%s' % host_id)

    def list_machines_or_hosts(self, mac=None, tag=None,
                               location=None, os_name=None,
                               os_id=None):
        data = {}
        if mac:
            data['mac'] = mac

        if tag:
            data['tag'] = tag

        if location:
            data['location'] = location

        if os_name:
            data['os_name'] = os_name

        if os_id:
            data['os_id'] = os_id

        return self._get('/machines-hosts', data=data)

    def get_machine_or_host(self, host_id):
        return self._get('/machines-hosts/%s' % host_id)

    def update_host(self, host_id, name=None,
                    reinstall_os=None, raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if name:
                data['name'] = name

            if reinstall_os:
                data['reinstall_os'] = reinstall_os

        return self._put('/hosts/%s' % host_id, data=data)

    def delete_host(self, host_id):
        return self._delete('/hosts/%s' % host_id)

    def get_host_clusters(self, host_id):
        return self._get('/hosts/%s/clusters' % host_id)

    def get_host_config(self, host_id):
        return self._get('/hosts/%s/config' % host_id)

    def update_host_config(self, host_id, os_config, raw_data=None):
        data = {}
        data['os_config'] = os_config
        if raw_data:
            data.update(raw_data)

        return self._put('/hosts/%s/config' % host_id, data=data)

    def patch_host_config(self, host_id, os_config, raw_data=None):
        data = {}
        data['os_config'] = os_config
        if raw_data:
            data.update(raw_data)

        return self._patch('/hosts/%s/config' % host_id, data=data)

    def delete_host_config(self, host_id):
        return self._delete('/hosts/%s/config' % host_id)

    def list_host_networks(self, host_id, interface=None, ip=None,
                           subnet=None, is_mgmt=None, is_promiscuous=None):
        data = {}
        if interface:
            data['interface'] = interface

        if ip:
            data['ip'] = ip

        if subnet:
            data['subnet'] = subnet

        if is_mgmt:
            data['is_mgmt'] = is_mgmt

        if is_promiscuous:
            data['is_promiscuous'] = is_promiscuous

        return self._get('/hosts/%s/networks' % host_id, data=data)

    def list_all_host_networks(self, interface=None, ip=None, subnet=None,
                               is_mgmt=None, is_promiscuous=None):
        data = {}
        if interface:
            data['interface'] = interface

        if ip:
            data['ip'] = ip

        if subnet:
            data['subnet'] = subnet

        if is_mgmt:
            data['is_mgmt'] = is_mgmt

        if is_promiscuous:
            data['is_promiscuous'] = is_promiscuous

        return self._get('/host-networks', data=data)

    def get_host_network(self, host_id, host_network_id):
        return self._get('/hosts/%s/networks/%s' %
                         (host_id, host_network_id))

    def get_network_for_all_hosts(self, host_network_id):
        return self._get('/host-networks/%s' % host_network_id)

    def add_host_network(self, host_id, interface, ip, subnet_id,
                         is_mgmt=None, is_promiscuous=None,
                         raw_data=None):
        data = {}
        data['interface'] = interface
        data['ip'] = ip
        data['subnet_id'] = subnet_id
        if raw_data:
            data.update(raw_data)
        else:
            if is_mgmt:
                data['is_mgmt'] = is_mgmt

            if is_promiscuous:
                data['is_promiscuous'] = is_promiscuous

        return self._post('/hosts/%s/networks' % host_id, data=data)

    def update_host_network(self, host_id, host_network_id,
                            ip=None, subnet_id=None, subnet=None,
                            is_mgmt=None, is_promiscuous=None,
                            raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if ip:
                data['ip'] = ip

            if subnet_id:
                data['subnet_id'] = subnet_id

            if subnet:
                data['subnet'] = subnet

            if is_mgmt:
                data['is_mgmt'] = is_mgmt

            if is_promiscuous:
                data['is_promiscuous'] = is_promiscuous

        return self._put('/hosts/%s/networks/%s' %
                         (host_id, host_network_id), data=data)

    def update_hostnetwork(self, host_network_id, ip=None,
                           subnet_id=None, subnet=None,
                           is_mgmt=None, is_promiscuous=None,
                           raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if ip:
                data['ip'] = ip

            if subnet_id:
                data['subnet_id'] = subnet_id

            if subnet:
                data['subnet'] = subnet

            if is_mgmt:
                data['is_mgmt'] = is_mgmt

            if is_promiscuous:
                data['is_promiscuous'] = is_promiscuous

        return self._put('/host-networks/%s' % host_network_id,
                         data=data)

    def delete_host_network(self, host_id, host_network_id):
        return self._delete('/hosts/%s/networks/%s',
                            (host_id, host_network_id))

    def delete_hostnetwork(self, host_network_id):
        return self._delete('/host-networks/%s' % host_network_id)

    def get_host_state(self, host_id):
        return self._get('/hosts/%s/state' % host_id)

    def update_host_state(self, host_id, state=None,
                          percentage=None, message=None,
                          raw_data=None):
        data = {}
        if raw_data:
            data = raw_data
        else:
            if state:
                data['state'] = state

            if percentage:
                data['percentage'] = percentage

            if message:
                data['message'] = message

        return self._put('/hosts/%s/state' % host_id, date=data)

    def poweron_host(self, host_id):
        data = {}
        data['poweron'] = True

        return self._post('/hosts/%s/action' % host_id, data=data)

    def poweroff_host(self, host_id):
        data = {}
        data['poweroff'] = True

        return self._post('/hosts/%s/action' % host_id, data=data)

    def reset_host(self, host_id):
        data = {}
        data['reset'] = True

        return self._post('/hosts/%s/action' % host_id, data=data)

    def clusterhost_ready(self, clusterhost_name):
        data = {}
        data['ready'] = True

        return self._post('/clusterhosts/%s/state_internal' %
                          clusterhost_name, data=data)
