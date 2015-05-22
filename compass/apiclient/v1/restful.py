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

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import json
import logging
import requests


class Client(object):
    """wrapper for compass restful api.

    .. note::
       Every api client method returns (status as int, resp as dict).
       If the api succeeds, the status is 2xx, the resp includes
       {'status': 'OK'} and other keys depend on method.
       If the api fails, the status is 4xx, the resp includes {
       'status': '...', 'message': '...'}
    """

    def __init__(self, url, headers=None, proxies=None, stream=None):
        """Restful api client initialization.

        :param url: url to the compass web service.
        :type url: str.
        :param headers: http header sent in each restful request.
        :type headers: dict of header name (str) to heade value (str).
        :param proxies: the proxy address for each protocol.
        :type proxies: dict of protocol (str) to proxy url (str).
        :param stream: wether the restful response should be streamed.
        :type stream: bool.
        """
        self.url_ = url
        self.session_ = requests.Session()
        if headers:
            self.session_.headers = headers

        if proxies is not None:
            self.session_.proxies = proxies

        if stream is not None:
            self.session_.stream = stream

    def __del__(self):
        self.session_.close()

    @classmethod
    def _get_response(cls, resp):
        """decapsulate the resp to status code and python formatted data."""
        resp_obj = {}
        try:
            resp_obj = resp.json()
        except Exception as error:
            logging.error('failed to load object from %s: %s',
                          resp.url, resp.content)
            logging.exception(error)
            resp_obj['status'] = 'Json Parsing Failure'
            resp_obj['message'] = resp.content

        return resp.status_code, resp_obj

    def _get(self, relative_url, params=None):
        """encapsulate get method."""
        url = '%s%s' % (self.url_, relative_url)
        if params:
            resp = self.session_.get(url, params=params)
        else:
            resp = self.session_.get(url)

        return self._get_response(resp)

    def _post(self, relative_url, data=None):
        """encapsulate post method."""
        url = '%s%s' % (self.url_, relative_url)
        if data:
            resp = self.session_.post(url, json.dumps(data))
        else:
            resp = self.session_.post(url)

        return self._get_response(resp)

    def _put(self, relative_url, data=None):
        """encapsulate put method."""
        url = '%s%s' % (self.url_, relative_url)
        if data:
            resp = self.session_.put(url, json.dumps(data))
        else:
            resp = self.session_.put(url)

        return self._get_response(resp)

    def _delete(self, relative_url):
        """encapsulate delete method."""
        url = '%s%s' % (self.url_, relative_url)
        return self._get_response(self.session_.delete(url))

    def get_switches(self, switch_ips=None, switch_networks=None, limit=None):
        """List details for switches.

        .. note::
           The switches can be filtered by switch_ips, siwtch_networks and
           limit. These params can be None or missing. If the param is None
           or missing, that filter will be ignored.

        :param switch_ips: Filter switch(es) with IP(s).
        :type switch_ips: list of str. Each is as 'xxx.xxx.xxx.xxx'.
        :param switch_networks: Filter switche(es) with network(s).
        :type switch_networks: list of str. Each is as 'xxx.xxx.xxx.xxx/xx'.
        :param limit: int, The maximum number of switches to return.
        :type limit: int. 0 means unlimited.
        """
        params = {}
        if switch_ips:
            params['switchIp'] = switch_ips

        if switch_networks:
            params['switchIpNetwork'] = switch_networks

        if limit:
            params['limit'] = limit
        return self._get('/switches', params=params)

    def get_switch(self, switch_id):
        """Lists details for a specified switch.

        :param switch_id: switch id.
        :type switch_id: int.
        """
        return self._get('/switches/%s' % switch_id)

    def add_switch(self, switch_ip, version=None, community=None,
                   username=None, password=None, raw_data=None):
        """Create a switch with specified details.

        .. note::
           It will trigger switch polling if successful. During
           the polling, MAC address of the devices connected to the
           switch will be learned by SNMP or SSH.

        :param switch_ip: the switch IP address.
        :type switch_ip: str, as xxx.xxx.xxx.xxx.
        :param version: SNMP version when using SNMP to poll switch.
        :type version: str, one in ['v1', 'v2c', 'v3']
        :param community: SNMP community when using SNMP to poll switch.
        :type community: str, usually 'public'.
        :param username: SSH username when using SSH to poll switch.
        :type username: str.
        :param password: SSH password when using SSH to poll switch.
        :type password: str.
        """
        data = {}
        if raw_data:
            data = raw_data
        else:
            data['switch'] = {}
            data['switch']['ip'] = switch_ip
            data['switch']['credential'] = {}
            if version:
                data['switch']['credential']['version'] = version

            if community:
                data['switch']['credential']['community'] = community

            if username:
                data['switch']['credential']['username'] = username

            if password:
                data['switch']['credential']['password'] = password

        return self._post('/switches', data=data)

    def update_switch(self, switch_id, ip_addr=None,
                      version=None, community=None,
                      username=None, password=None,
                      raw_data=None):
        """Updates a switch with specified details.

        .. note::
           It will trigger switch polling if successful. During
           the polling, MAC address of the devices connected to the
           switch will be learned by SNMP or SSH.

        :param switch_id: switch id
        :type switch_id: int.
        :param ip_addr: the switch ip address.
        :type ip_addr: str, as 'xxx.xxx.xxx.xxx' format.
        :param version: SNMP version when using SNMP to poll switch.
        :type version: str, one in ['v1', 'v2c', 'v3'].
        :param community: SNMP community when using SNMP to poll switch.
        :type community: str, usually be 'public'.
        :param username: username when using SSH to poll switch.
        :type username: str.
        :param password: password when using SSH to poll switch.
        """
        data = {}
        if raw_data:
            data = raw_data
        else:
            data['switch'] = {}
            if ip_addr:
                data['switch']['ip'] = ip_addr

            data['switch']['credential'] = {}
            if version:
                data['switch']['credential']['version'] = version

            if community:
                data['switch']['credential']['community'] = community

            if username:
                data['switch']['credential']['username'] = username

            if password:
                data['switch']['credential']['password'] = password

        return self._put('/switches/%s' % switch_id, data=data)

    def delete_switch(self, switch_id):
        """Not implemented in api."""
        return self._delete('/switches/%s' % switch_id)

    def get_machines(self, switch_id=None, vlan_id=None,
                     port=None, limit=None):
        """Get the details of machines.

        .. note::
           The machines can be filtered by switch_id, vlan_id, port
           and limit. These params can be None or missing. If the param
           is None or missing, the filter will be ignored.

        :param switch_id: Return machine(s) connected to the switch.
        :type switch_id: int.
        :param vlan_id: Return machine(s) belonging to the vlan.
        :type vlan_id: int.
        :param port: Return machine(s) connect to the port.
        :type port: int.
        :param limit: the maximum number of machines will be returned.
        :type limit: int. 0 means no limit.
        """
        params = {}
        if switch_id:
            params['switchId'] = switch_id

        if vlan_id:
            params['vlanId'] = vlan_id

        if port:
            params['port'] = port

        if limit:
            params['limit'] = limit

        return self._get('/machines', params=params)

    def get_machine(self, machine_id):
        """Lists the details for a specified machine.

        :param machine_id: Return machine with the id.
        :type machine_id: int.
        """
        return self._get('/machines/%s' % machine_id)

    def get_clusters(self):
        """Lists the details for all clusters."""
        return self._get('/clusters')

    def get_cluster(self, cluster_id):
        """Lists the details of the specified cluster.

        :param cluster_id: cluster id.
        :type cluster_id: int.
        """
        return self._get('/clusters/%d' % cluster_id)

    def add_cluster(self, cluster_name, adapter_id, raw_data=None):
        """Creates a cluster by specified name and given adapter id.

        :param cluster_name: cluster name.
        :type cluster_name: str.
        :param adapter_id: adapter id.
        :type adapter_id: int.
        """
        data = {}
        if raw_data:
            data = raw_data
        else:
            data['cluster'] = {}
            data['cluster']['name'] = cluster_name
            data['cluster']['adapter_id'] = adapter_id
        return self._post('/clusters', data=data)

    def add_hosts(self, cluster_id, machine_ids, raw_data=None):
        """add the specified machine(s) as the host(s) to the cluster.

        :param cluster_id: cluster id.
        :type cluster_id: int.
        :param machine_ids: machine ids to add to cluster.
        :type machine_ids: list of int, each is the id of one machine.
        """
        data = {}
        if raw_data:
            data = raw_data
        else:
            data['addHosts'] = machine_ids
        return self._post('/clusters/%d/action' % cluster_id, data=data)

    def remove_hosts(self, cluster_id, host_ids, raw_data=None):
        """remove the specified host(s) from the cluster.

        :param cluster_id: cluster id.
        :type cluster_id: int.
        :param host_ids: host ids to remove from cluster.
        :type host_ids: list of int, each is the id of one host.
        """
        data = {}
        if raw_data:
            data = raw_data
        else:
            data['removeHosts'] = host_ids
        return self._post('/clusters/%s/action' % cluster_id, data=data)

    def replace_hosts(self, cluster_id, machine_ids, raw_data=None):
        """replace the cluster hosts with the specified machine(s).

        :param cluster_id: int, The unique identifier of the cluster.
        :type cluster_id: int.
        :param machine_ids: the machine ids to replace the hosts in cluster.
        :type machine_ids: list of int, each is the id of one machine.
        """
        data = {}
        if raw_data:
            data = raw_data
        else:
            data['replaceAllHosts'] = machine_ids
        return self._post('/clusters/%s/action' % cluster_id, data=data)

    def deploy_hosts(self, cluster_id, raw_data=None):
        """Deploy the cluster.

        :param cluster_id: The unique identifier of the cluster
        :type cluster_id: int.
        """
        data = {}
        if raw_data:
            data = raw_data
        else:
            data['deploy'] = []
        return self._post('/clusters/%d/action' % cluster_id, data=data)

    @classmethod
    def parse_security(cls, kwargs):
        """parse the arguments to security data."""
        data = {}
        for key, value in kwargs.items():
            if '_' not in key:
                continue
            key_name, key_value = key.split('_', 1)
            data.setdefault(
                '%s_credentials' % key_name, {})[key_value] = value

        return data

    def set_security(self, cluster_id, **kwargs):
        """Update the cluster security configuration.

        :param cluster_id: cluster id.
        :type cluster_id: int.
        :param <security_name>_username: username of the security name.
        :type <security_name>_username: str.
        :param <security_name>_password: passowrd of the security name.
        :type <security_name>_password: str.

        .. note::
           security_name should be one of ['server', 'service', 'console'].
        """
        data = {}
        data['security'] = self.parse_security(kwargs)
        return self._put('/clusters/%d/security' % cluster_id, data=data)

    @classmethod
    def parse_networking(cls, kwargs):
        """parse arguments to network data."""
        data = {}
        global_keys = [
            'nameservers', 'search_path', 'gateway',
            'proxy', 'ntp_server', 'ha_vip']
        for key, value in kwargs.items():
            if key in global_keys:
                data.setdefault('global', {})[key] = value
            else:
                if '_' not in key:
                    continue

                key_name, key_value = key.split('_', 1)
                data.setdefault(
                    'interfaces', {}
                ).setdefault(
                    key_name, {}
                )[key_value] = value

        return data

    def set_networking(self, cluster_id, **kwargs):
        """Update the cluster network configuration.

        :param cluster_id: cluster id.
        :type cluster_id: int.
        :param nameservers: comma seperated nameserver ip address.
        :type nameservers: str.
        :param search_path: comma seperated dns name search path.
        :type search_path: str.
        :param gateway: gateway ip address for routing to outside.
        :type gateway: str.
        :param proxy: proxy url for downloading packages.
        :type proxy: str.
        :param ntp_server: ntp server ip address to sync timestamp.
        :type ntp_server: str.
        :param ha_vip: ha vip address to run ha proxy.
        :type ha_vip: str.
        :param <interface>_ip_start: start ip address to host's interface.
        :type <interface>_ip_start: str.
        :param <interface>_ip_end: end ip address to host's interface.
        :type <interface>_ip_end: str.
        :param <interface>_netmask: netmask to host's interface.
        :type <interface>_netmask: str.
        :param <interface>_nic: host physical interface name.
        :type <interface>_nic: str.
        :param <interface>_promisc: if the interface in promiscous mode.
        :type <interface>_promisc: int, 0 or 1.

        .. note::
           interface should be one of ['management', 'tenant',
           'public', 'storage'].
        """
        data = {}
        data['networking'] = self.parse_networking(kwargs)
        return self._put('/clusters/%d/networking' % cluster_id, data=data)

    @classmethod
    def parse_partition(cls, kwargs):
        """parse arguments to partition data."""
        data = {}
        for key, value in kwargs.items():
            if key.endswith('_percentage'):
                key_name = key[:-len('_percentage')]
                data[key_name] = '%s%%' % value
            elif key.endswitch('_mbytes'):
                key_name = key[:-len('_mbytes')]
                data[key_name] = str(value)

        return ';'.join([
            '/%s %s' % (key, value) for key, value in data.items()
        ])

    def set_partition(self, cluster_id, **kwargs):
        """Update the cluster partition configuration.

        :param cluster_id: cluster id.
        :type cluster_id: int.
        :param <partition>_percentage: the partiton percentage.
        :type <partition>_percentage: float between 0 to 100.
        :param <partition>_mbytes: the partition mbytes.
        :type <partition>_mbytes: int.

        .. note::
           partition should be one of ['home', 'var', 'tmp'].
        """
        data = {}
        data['partition'] = self.parse_partition(kwargs)
        return self._put('/clusters/%s/partition' % cluster_id, data=data)

    def get_hosts(self, hostname=None, clustername=None):
        """Lists the details of hosts.

        .. note::
           The hosts can be filtered by hostname, clustername.
           These params can be None or missing. If the param
           is None or missing, the filter will be ignored.

        :param hostname: The name of a host.
        :type hostname: str.
        :param clustername: The name of a cluster.
        :type clustername: str.
        """
        params = {}
        if hostname:
            params['hostname'] = hostname

        if clustername:
            params['clustername'] = clustername

        return self._get('/clusterhosts', params=params)

    def get_host(self, host_id):
        """Lists the details for the specified host.

        :param host_id: host id.
        :type host_id: int.
        """
        return self._get('/clusterhosts/%s' % host_id)

    def get_host_config(self, host_id):
        """Lists the details of the config for the specified host.

        :param host_id: host id.
        :type host_id: int.
        """
        return self._get('/clusterhosts/%s/config' % host_id)

    def update_host_config(self, host_id, hostname=None,
                           roles=None, raw_data=None, **kwargs):
        """Updates config for the host.

        :param host_id: host id.
        :type host_id: int.
        :param hostname: host name.
        :type hostname: str.
        :param security_<security>_username: username of the security name.
        :type security_<security>_username: str.
        :param security_<security>_password: passowrd of the security name.
        :type security_<security>_password: str.
        :param networking_nameservers: comma seperated nameserver ip address.
        :type networking_nameservers: str.
        :param networking_search_path: comma seperated dns name search path.
        :type networking_search_path: str.
        :param networking_gateway: gateway ip address for routing to outside.
        :type networking_gateway: str.
        :param networking_proxy: proxy url for downloading packages.
        :type networking_proxy: str.
        :param networking_ntp_server: ntp server ip address to sync timestamp.
        :type networking_ntp_server: str.
        :param networking_<interface>_ip: ip address to host interface.
        :type networking_<interface>_ip: str.
        :param networking_<interface>_netmask: netmask to host's interface.
        :type networking_<interface>_netmask: str.
        :param networking_<interface>_nic: host physical interface name.
        :type networking_<interface>_nic: str.
        :param networking_<interface>_promisc: if the interface is promiscous.
        :type networking_<interface>_promisc: int, 0 or 1.
        :param partition_<partition>_percentage: the partiton percentage.
        :type partition_<partition>_percentage: float between 0 to 100.
        :param partition_<partition>_mbytes: the partition mbytes.
        :type partition_<partition>_mbytes: int.
        :param roles: host assigned roles in the cluster.
        :type roles: list of str.
        """
        data = {}
        if raw_data:
            data = raw_data
        else:
            if hostname:
                data['hostname'] = hostname

            sub_kwargs = {}
            for key, value in kwargs.items():
                key_name, key_value = key.split('_', 1)
                sub_kwargs.setdefault(key_name, {})[key_value] = value

            if 'security' in sub_kwargs:
                data['security'] = self.parse_security(sub_kwargs['security'])

            if 'networking' in sub_kwargs:
                data['networking'] = self.parse_networking(
                    sub_kwargs['networking'])
            if 'partition' in sub_kwargs:
                data['partition'] = self.parse_partition(
                    sub_kwargs['partition'])

            if roles:
                data['roles'] = roles

        return self._put('/clusterhosts/%s/config' % host_id, data)

    def delete_from_host_config(self, host_id, delete_key):
        """Deletes one key in config for the host.

        :param host_id: host id.
        :type host_id: int.
        :param delete_key: the key in host config to be deleted.
        :type delete_key: str.
        """
        return self._delete('/clusterhosts/%s/config/%s' % (
            host_id, delete_key))

    def get_adapters(self, name=None):
        """Lists details of adapters.

        .. note::
           the adapter can be filtered by name of name is given and not None.

        :param name: adapter name.
        :type name: str.
        """
        params = {}
        if name:
            params['name'] = name

        return self._get('/adapters', params=params)

    def get_adapter(self, adapter_id):
        """Lists details for the specified adapter.

        :param adapter_id: adapter id.
        :type adapter_id: int.
        """
        return self._get('/adapters/%s' % adapter_id)

    def get_adapter_roles(self, adapter_id):
        """Lists roles to assign to hosts for the specified adapter.

        :param adapter_id: adapter id.
        :type adapter_id: int.
        """
        return self._get('/adapters/%s/roles' % adapter_id)

    def get_host_installing_progress(self, host_id):
        """Lists progress details for the specified host.

        :param host_id: host id.
        :type host_id: int.
        """
        return self._get('/clusterhosts/%s/progress' % host_id)

    def get_cluster_installing_progress(self, cluster_id):
        """Lists progress details for the specified cluster.

        :param cluster_id: cluster id.
        :param cluster_id: int.
        """

        return self._get('/clusters/%s/progress' % cluster_id)

    def get_dashboard_links(self, cluster_id):
        """Lists links for dashboards of deployed cluster.

        :param cluster_id: cluster id.
        :type cluster_id: int.
        """
        params = {}
        params['cluster_id'] = cluster_id
        return self._get('/dashboardlinks', params)
