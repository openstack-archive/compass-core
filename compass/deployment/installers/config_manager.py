from collections import defaultdict
from copy import deepcopy
import logging
import netaddr
import json

from compass.deployment.utils import constants as const

ip_generator_map = {}
def get_ip_addr(ip_ranges):
    def _get_ip_addr():
        for ip_range in ip_ranges:
            for ip in netaddr.iter_iprange(*ip_range):
                yield str(ip)

    s = json.dumps(ip_ranges)
    if s not in ip_generator_map:
        ip_generator_map[s] = _get_ip_addr()
        return ip_generator_map[s]
    else:
        return ip_generator_map[s]

class AdapterInfo(object):
    def __init__(self, adapter_info):
        self.adapter_info = adapter_info
        self.name =  self.adapter_info.get(const.NAME)
        self.dist_system_name = self.name
        self.health_check_cmd = self.adapter_info.get(const.HEALTH_CHECK_CMD)

        self.os_installer = self.adapter_info.setdefault(const.OS_INSTALLER, {})
        self.os_installer.setdefault(const.INSTALLER_SETTINGS, {})

        self.package_installer = self.adapter_info.setdefault(const.PK_INSTALLER, {})
        self.package_installer.setdefault(const.INSTALLER_SETTINGS, {})

        self.metadata = self.adapter_info.setdefault(const.METADATA, {})
        self.os_metadata = self.metadata.setdefault(const.OS_CONFIG, {})
        self.package_metadata = self.metadata.setdefault(const.PK_CONFIG, {})

        self.flavors = dict([(f[const.FLAVOR_NAME], f) for f in self.adapter_info.get(const.FLAVOR, [])])

    @property
    def flavor_list(self):
        return self.flavors.values()

    def get_flavor(self, flavor_name):
        return self.flavors.get(flavor_name)

class ClusterInfo(object):
    def __init__(self, cluster_info):
        self.cluster_info = cluster_info
        self.id = self.cluster_info.get(const.ID)
        self.name = self.cluster_info.get(const.NAME)
        self.os_version = self.cluster_info.get(const.OS_VERSION)
        self.flavor = self.cluster_info.setdefault(const.FLAVOR, {})
        self.os_config = self.cluster_info.setdefault(const.OS_CONFIG, {})
        self.package_config = self.cluster_info.setdefault(const.PK_CONFIG, {})
        self.deployed_os_config = self.cluster_info.setdefault(const.DEPLOYED_OS_CONFIG, {})
        self.deployed_package_config = self.cluster_info.setdefault(const.DEPLOYED_PK_CONFIG, {})
        self.network_mapping = self.package_config.setdefault(const.NETWORK_MAPPING, {})

        os_config_general = self.os_config.setdefault(const.OS_CONFIG_GENERAL, {})
        self.domain = os_config_general.setdefault(const.DOMAIN, None)
        self.hosts = []

    def add_host(self, host):
        self.hosts.append(host)

    @property
    def roles_mapping(self):
        deploy_config = self.deployed_package_config
        return deploy_config.setdefault(const.ROLES_MAPPING, self._get_cluster_roles_mapping())

    def _get_cluster_roles_mapping(self):
        """The ouput format will be as below, for example:

        {
            "controller": [{
                "hostname": "xxx",
                "management": {
                    "interface": "eth0",
                    "ip": "192.168.1.10",
                    "netmask": "255.255.255.0",
                    "subnet": "192.168.1.0/24",
                    "is_mgmt": True,
                    "is_promiscuous": False
                },
                ...
            }],
                ...
        }
        """
        mapping = defaultdict(list)
        for host in self.hosts:
            for role, value in host.roles_mapping.iteritems():
                mapping[role].append(value)

        return dict(mapping)

    @property
    def base_info(self):
        return { const.ID: self.id,
                 const.NAME: self.name,
                 const.OS_VERSION: self.os_version }

class HostInfo(object):
    def __init__(self, host_info, cluster_info):
        self.host_info = host_info
        self.cluster_info = cluster_info
        self.id = self.host_info.get(const.ID)
        self.name = self.host_info.get(const.NAME)
        self.mac = self.host_info.get(const.MAC_ADDR)
        self.hostname = self.host_info.get(const.HOSTNAME)
        self.networks = self.host_info.setdefault(const.NETWORKS, {})
        self.os_config = self.host_info.setdefault(const.OS_CONFIG, {})

        self.package_config = self.host_info.setdefault(const.PK_CONFIG, {})
        self.roles = self.host_info.setdefault(const.ROLES, [])
        self.ipmi = deepcopy(self.host_info.setdefault(const.IPMI, {}))
        self.reinstall_os_flag = self.host_info.get(const.REINSTALL_OS_FLAG)
        self.deployed_os_config = self.host_info.setdefault(const.DEPLOYED_OS_CONFIG, {})
        self.deployed_package_config = self.host_info.setdefault(const.DEPLOYED_PK_CONFIG, {})

        os_general_config = self.os_config.setdefault(const.OS_CONFIG_GENERAL, {})
        domain = os_general_config.setdefault(const.DOMAIN, None)
        if domain is None:
            self.domain = self.cluster_info.domain
        else:
            self.domain = domain

        if const.DNS in host_info:
            self.dns = host_info[const.DNS]
        else:
            self.dns = '.'.join((self.hostname, self.domain))

        if const.NETWORK_MAPPING not in self.package_config:
            self.network_mapping = self.cluster_info.network_mapping
        else:
            self.network_mapping = self.package_config[const.NETWORK_MAPPING]

        if const.ROLES_MAPPING not in self.deployed_package_config:
            self.roles_mapping = self._get_host_roles_mapping()
            self.deployed_package_config[const.ROLES_MAPPING] = self.roles_mapping
        else:
            self.roles_mapping  = self.deployed_package_config[const.ROLES_MAPPING]

        self.cluster_info.add_host(self)

    def valid_interface(self, interface):
        if interface not in self.networks:
            raise RuntimeError("interface %s is invalid" % interface)

    def get_interface(self, interface):
        self.valid_interface(interface)
        return self.networks[interface]

    def get_interface_ip(self, interface):
        return self.get_interface(interface).get(const.IP_ADDR)

    def get_interface_netmask(self, interface):
        return self.get_interface(interface).get(const.NETMASK)

    def get_interface_subnet(self, interface):
        return self.get_interface(interface).get(const.SUBNET)

    def is_interface_promiscuous(self, interface):
        return self.get_interface(interface).get(const.PROMISCUOUS_FLAG)

    def is_interface_mgmt(self, interface):
        return self.get_interface(interface).get(const.MGMT_NIC_FLAG)

    def _get_host_roles_mapping(self):
        if not self.network_mapping:
            return {}

        net_info = {const.HOSTNAME: self.hostname}
        for k, v in self.network_mapping.items():
            try:
                net_info[k] = self.networks[v[const.NIC]]
                net_info[k][const.NIC] = v[const.NIC]
            except:
                pass

        mapping = {}
        for role in self.roles:
            role = role.replace("-", "_")
            mapping[role] = net_info

        return mapping

    @property
    def baseinfo(self):
        return  { const.REINSTALL_OS_FLAG: self.reinstall_os_flag,
                  const.MAC_ADDR: self.mac,
                  const.NAME: self.name,
                  const.HOSTNAME: self.hostname,
                  const.DNS: self.dns,
                  const.NETWORKS: deepcopy(self.networks) }

class BaseConfigManager(object):
    def __init__(self, adapter_info={}, cluster_info={}, hosts_info={}):
        assert(adapter_info and isinstance(adapter_info, dict))
        assert(cluster_info and isinstance(adapter_info, dict))
        assert(hosts_info and isinstance(adapter_info, dict))

        self.adapter_info = AdapterInfo(adapter_info)
        self.cluster_info = ClusterInfo(cluster_info)
        self.hosts_info = dict([(k, HostInfo(v, self.cluster_info)) for k, v in hosts_info.iteritems()])

    #*************************** adapter method start ****************************
    def get_adapter_name(self):
        return self.adapter_info.name

    def get_dist_system_name(self):
        return self.adapter_info.dist_system_name

    def get_adapter_health_check_cmd(self):
        return self.adapter_info.health_check_cmd

    def get_os_installer_settings(self):
        return self.adapter_info.os_installer[const.INSTALLER_SETTINGS]

    def get_pk_installer_settings(self):
        return self.adapter_info.package_installer[const.INSTALLER_SETTINGS]

    def get_os_config_metadata(self):
        return  self.adapter_info.metadata[const.OS_CONFIG]

    def get_pk_config_meatadata(self):
        return  self.adapter_info.metadata[const.PK_CONFIG]

    def get_adapter_all_flavors(self):
        return  self.adapter_info.flavor_list

    def get_adapter_flavor(self, flavor_name):
        return self.adapter_info.get_flavor(flavor_name)

    #*************************** adapter method end ****************************
    #*************************** cluster method start ****************************
    def get_cluster_id(self):
        return self.cluster_info.id

    def get_clustername(self):
        return self.cluster_info.name

    def get_os_version(self):
        return self.cluster_info.os_version

    def get_cluster_os_config(self):
        return self.cluster_info.os_config

    def get_cluster_baseinfo(self):
        return self.cluster_info.base_info

    def get_cluster_flavor_name(self):
        return self.cluster_info.flavor.get(const.FLAVOR_NAME)

    def get_cluster_flavor_roles(self):
        return self.cluster_info.flavor.get(const.ROLES, [])

    def get_cluster_flavor_template(self):
        return self.cluster_info.flavor.get(const.TMPL)

    def get_cluster_package_config(self):
        return self.cluster_info.package_config

    def get_cluster_network_mapping(self):
        mapping = self.cluster_info.network_mapping
        logging.info("Network mapping in the config is '%s'!", mapping)
        return mapping

    def get_cluster_deployed_os_config(self):
        return self.cluster_info.deployed_os_config

    def get_cluster_deployed_package_config(self):
        return self.cluster_info.deployed_package_config

    def get_cluster_roles_mapping(self):
        return self.cluster_info.roles_mapping

    #*************************** cluster method end ****************************

    #*************************** host method start ****************************
    def validate_host(self, host_id):
        if host_id not in self.hosts_info:
            raise RuntimeError("host_id %s is invalid" % host_id)

    def get_host_id_list(self):
        return self.hosts_info.keys()

    def get_hosts_id_list_for_os_installation(self):
        """Get info of hosts which need to install/reinstall OS."""
        return [id for id, info in self.hosts_info.items() if info.reinstall_os_flag]

    def get_server_credentials(self):
        cluster_os_config = self.get_cluster_os_config()
        if not cluster_os_config:
            logging.info("cluster os_config is None!")
            return ()

        username = cluster_os_config[const.SERVER_CREDS][const.USERNAME]
        password = cluster_os_config[const.SERVER_CREDS][const.PASSWORD]
        return (username, password)

    def _get_host_info(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id]

    def get_host_baseinfo(self, host_id):
        self.validate_host(host_id)
        host_info = self.hosts_info[host_id]
        return host_info.baseinfo

    def get_host_fullname(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].name

    def get_host_dns(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].dns

    def get_host_mac_address(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].mac

    def get_hostname(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].hostname

    def get_host_networks(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].networks

    def get_host_interfaces(self, host_id):
        # get interface names
        return self.get_host_networks(host_id).keys()

    def get_host_interface_ip(self, host_id, interface):
        self.validate_host(host_id)
        return self.hosts_info[host_id].get_interface_ip(interface)

    def get_host_interface_netmask(self, host_id, interface):
        self.validate_host(host_id)
        return self.hosts_info[host_id].get_interface_netmask(interface)

    def get_host_interface_subnet(self, host_id, interface):
        self.validate_host(host_id)
        return self.hosts_info[host_id].get_interface_subnet(interface)

    def is_interface_promiscuous(self, host_id, interface):
        self.validate_host(host_id)
        return self.hosts_info[host_id].is_interface_promiscuous(interface)

    def is_interface_mgmt(self, host_id, interface):
        self.validate_host(host_id)
        return self.hosts_info[host_id].is_interface_mgmt(interface)

    def get_host_os_config(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].os_config

    def get_host_domain(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].domain

    def get_host_network_mapping(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].network_mapping

    def get_host_package_config(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].package_config

    def get_host_deployed_os_config(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].deployed_os_config

    def get_host_deployed_package_config(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].deployed_package_config

    def get_host_roles(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].roles

    def get_all_hosts_roles(self, hosts_id_list=None):
        roles = []
        for host_id, host_info in self.hosts_info.iteritems():
            roles.extend(host_info.roles)

        return list(set(roles))

    def get_hosts_ip_settings(self, ip_settings, sys_intf_mappings):
        logging.info("get_hosts_ip_settings:ip_settings=%s, sys_intf_mappings=%s" \
                % (ip_settings, sys_intf_mappings))

        intf_alias = {}
        for m in sys_intf_mappings:
            if "vlan_tag" in m:
                intf_alias[m["name"]] = m["name"]
            else:
                intf_alias[m["name"]] = m["interface"]

        mappings = {}
        hosts_id_list = self.get_host_id_list()
        for host_id in hosts_id_list:
            hostname = self.get_hostname(host_id)
            mappings[hostname] = []
            for ip_info in ip_settings:
                logging.info("ip_info=%s" % ip_info)
                new_ip_info = deepcopy(ip_info)
                del new_ip_info["ip_ranges"]

                ip_ranges = ip_info["ip_ranges"]
                new_ip_info["netmask"] = netaddr.IPNetwork(ip_info["cidr"]).netmask.bin.count("1")
                new_ip_info["ip"] = get_ip_addr(ip_ranges).next()
                new_ip_info["alias"] = intf_alias[ip_info["name"]]
                mappings[hostname].append(new_ip_info)

        #ugly design
        return {"ip_settings": mappings}

    def get_host_roles_mapping(self, host_id):
        self.validate_host(host_id)
        return self.hosts_info[host_id].roles_mapping

    def get_host_ipmi_info(self, host_id):
        self.validate_host(host_id)
        if self.hosts_info[host_id].ipmi:
            return (self.hosts_info[host_id].ipmi[const.IP_ADDR],
                    self.hosts_info[host_id].ipmi[const.IPMI_CREDS][const.USERNAME],
                    self.hosts_info[host_id].ipmi[const.IPMI_CREDS][const.USERNAME])
        else:
            return (None, None, None)

    #*************************** host method end ****************************

