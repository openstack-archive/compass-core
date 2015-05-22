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

"""deploy cluster from csv file."""
import ast
import copy
import csv
import os
import re
import sys

from multiprocessing import Process
from multiprocessing import Queue
from optparse import OptionParser

try:
    from compass.apiclient.restful import Client
except ImportError:
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    apiclient_dir = os.path.dirname(curr_dir) + '/compass/apiclient'
    sys.path.append(apiclient_dir)
    from restful import Client


DELIMITER = ","

# Sqlite tables
TABLES = {
    'switch_config': {'columns': ['id', 'ip', 'filter_port']},
    'switch': {'columns': ['id', 'ip', 'credential_data']},
    'machine': {'columns': ['id', 'mac', 'port', 'vlan', 'switch_id']},
    'cluster': {'columns': ['id', 'name', 'security_config',
                            'networking_config', 'partition_config',
                            'adapter_id', 'state']},
    'cluster_host': {'columns': ['id', 'cluster_id', 'hostname', 'machine_id',
                                 'config_data', 'state']},
    'adapter': {'columns': ['id', 'name', 'os', 'target_system']},
    'role': {'columns': ['id', 'name', 'target_system', 'description']}
}


def start(csv_dir, compass_url):
    """Start deploy both failed clusters and new clusters."""
    # Get clusters and hosts data from CSV
    clusters_data = get_csv('cluster.csv', csv_dir)
    hosts_data = get_csv('cluster_host.csv', csv_dir)
    data = {}
    for cluster in clusters_data:
        tmp = {}
        tmp['cluster_data'] = cluster
        tmp['hosts_data'] = []
        data[cluster['id']] = tmp

    for host in hosts_data:
        cluster_id = host['cluster_id']
        if cluster_id not in data:
            print ("Unknown cluster_id=%s of the host! host_id=%s!"
                   % (cluster_id, host['id']))
            sys.exit(1)

        data[cluster_id]['hosts_data'].append(host)

    apiClient = _APIClient(compass_url)
    results_q = Queue()
    ps = []
    for elem in data:
        cluster_data = data[elem]['cluster_data']
        hosts_data = data[elem]['hosts_data']
        p = Process(target=apiClient.execute,
                    args=(cluster_data, hosts_data, results_q))
        ps.append(p)
        p.start()

    for p in ps:
        p.join()

    progress_file = '/'.join((csv_dir, 'progress.csv'))
    write_progress_to_file(results_q, progress_file)


def write_progress_to_file(results_q, progress_file):
    cluster_headers = ['cluster_id', 'progress_url']
    host_headers = ['host_id', 'progress_url']

    with open(progress_file, 'wb') as f:
        print "Writing all progress information to %s......" % progress_file
        writer = csv.writer(f, delimiter=DELIMITER, quoting=csv.QUOTE_MINIMAL)
        while not results_q.empty():
            record = results_q.get()
            hosts = []
            cluster = [record['deployment']['cluster']['cluster_id'],
                       record['deployment']['cluster']['url']]
            writer.writerow(cluster_headers)
            writer.writerow(cluster)

            for elem in record['deployment']['hosts']:
                host = [elem['host_id'], elem['url']]
                hosts.append(host)

            writer.writerow(host_headers)
            writer.writerows(hosts)
    print "Done!\n"


def get_csv(fname, csv_dir):
    """Parse csv files into python variables.

       .. note::
          all nested fields in db will be assembled.

        :param fname: CSV file name
        :param csv_dir: CSV files directory

        :returns: list of dict which key is column name and value is its data.
    """
    headers = []
    rows = []
    file_dir = '/'.join((csv_dir, fname))
    with open(file_dir) as f:
        reader = csv.reader(f, delimiter=DELIMITER, quoting=csv.QUOTE_MINIMAL)
        headers = reader.next()
        rows = [x for x in reader]

    result = []
    for row in rows:
        data = {}
        for col_name, value in zip(headers, row):
            if re.match(r'^[\d]+$', value):
                # the value should be an integer
                value = int(value)
            elif re.match(r'^\[(\'\w*\'){1}(\s*,\s*\'\w*\')*\]$', value):
                # the value should be a list
                value = ast.literal_eval(value)
            elif value == 'None':
                value = ''

            if col_name.find('.') > 0:
                tmp_result = {}
                tmp_result[col_name.split('.')[-1]] = value
                keys = col_name.split('.')[::-1][1:]
                for key in keys:
                    tmp = {}
                    tmp[key] = tmp_result
                    tmp_result = tmp
                    merge_dict(data, tmp_result)
            else:
                data[col_name] = value

        result.append(data)

    return result


def merge_dict(lhs, rhs, override=True):
    """Merge nested right dict into left nested dict recursively.

    :param lhs: dict to be merged into.
    :type lhs: dict
    :param rhs: dict to merge from.
    :type rhs: dict
    :param override: the value in rhs overide the value in left if True.
    :type override: str

    :raises: TypeError if lhs or rhs is not a dict.
    """
    if not rhs:
        return

    if not isinstance(lhs, dict):
        raise TypeError('lhs type is %s while expected is dict' % type(lhs),
                        lhs)

    if not isinstance(rhs, dict):
        raise TypeError('rhs type is %s while expected is dict' % type(rhs),
                        rhs)

    for key, value in rhs.items():
        if isinstance(value, dict) and key in lhs and isinstance(lhs[key],
                                                                 dict):
            merge_dict(lhs[key], value, override)
        else:
            if override or key not in lhs:
                lhs[key] = copy.deepcopy(value)


class _APIClient(Client):
    def __init__(self, url, headers=None, proxies=None, stream=None):
        super(_APIClient, self).__init__(url, headers, proxies, stream)

    def set_cluster_resource(self, cluster_id, resource, data):
        url = "/clusters/%d/%s" % (cluster_id, resource)
        return self._put(url, data=data)

    def execute(self, cluster_data, hosts_data, resp_results):
        """The process includes creating or updating a cluster.

        The cluster configuration, add or update a host in the cluster,
        and deploy the updated hosts.

        :param cluster_data: the dictionary of cluster data
        """
        cluster_id = cluster_data['id']
        code, resp = self.get_cluster(cluster_id)
        if code == 404:
            # Create a new cluster
            name = cluster_data['name']
            adapter_id = cluster_data['adapter_id']
            code, resp = self.add_cluster(name, adapter_id)

            if code != 200:
                print ("Failed to create the cluster which name is "
                       "%s!\nError message: %s" % (name, resp['message']))
                sys.exit(1)

        # Update the config(security, networking, partition) of the cluster
        security_req = {}
        networking_req = {}
        partition_req = {}

        security_req['security'] = cluster_data['security_config']
        networking_req['networking'] = cluster_data['networking_config']
        partition_req['partition'] = cluster_data['partition_config']

        print "Update Security config......."
        code, resp = self.set_cluster_resource(cluster_id, 'security',
                                               security_req)
        if code != 200:
            print ("Failed to update Security config for cluster id=%s!\n"
                   "Error message: " % (cluster_id, resp['message']))
            sys.exit(1)

        print "Update Networking config......."
        code, resp = self.set_cluster_resource(cluster_id, 'networking',
                                               networking_req)
        if code != 200:
            print ("Failed to update Networking config for cluster id=%s!\n"
                   "Error message: %s" % (cluster_id, resp['message']))
            sys.exit(1)

        print "Update Partition config......."
        code, resp = self.set_cluster_resource(cluster_id, 'partition',
                                               partition_req)
        if code != 200:
            print ("Failed to update Partition config for cluster id=%s!\n"
                   "Error message: " % (cluster_id, resp['message']))
            sys.exit(1)

        deploy_list = []
        deploy_hosts_data = []

        machines_list = []
        new_hosts_data = []
        for record in hosts_data:
            if record['state'] and int(record['deploy_action']):
                deploy_list.append(record['id'])
                deploy_hosts_data.append(record)

            elif int(record['deploy_action']):
                machines_list.append(record['machine_id'])
                new_hosts_data.append(record)

        if machines_list:
            # add new hosts to the cluster
            code, resp = self.add_hosts(cluster_id, machines_list)
            if code != 200:
                print ("Failed to add hosts to the cluster id=%s!\n"
                       "Error message: %s.\nfailed hosts are %s"
                       % (cluster_id, resp['message'], resp['failedMachines']))
                sys.exit(1)

            for record, host in zip(new_hosts_data, resp['cluster_hosts']):
                record['id'] = host['id']
                deploy_list.append(host['id'])
                deploy_hosts_data.append(record)

        # Update the config of each host in the cluster
        for host in deploy_hosts_data:
            req = {}
            host_id = host['id']
            print "Updating the config of host id=%s" % host['id']
            req['hostname'] = host['hostname']
            req.update(host['config_data'])
            code, resp = self.update_host_config(int(host_id), raw_data=req)
            if code != 200:
                print ("Failed to update the config of the host id=%s!\n"
                       "Error message: %s" % (host_id, resp['message']))
                sys.exit(1)

        # Start to deploy the cluster
        print "Start to deploy the cluster!....."
        deploy_req = {"deploy": deploy_list}
        code, resp = self.deploy_hosts(cluster_id, raw_data=deploy_req)
        print "---Cluster Info---"
        print "cluster_id  url"
        print ("    %s     %s"
               % (resp['deployment']['cluster']['cluster_id'],
                  resp['deployment']['cluster']['url']))
        print "---Hosts Info-----"
        print "host_id  url"
        for host in resp['deployment']['hosts']:
            print "    %s     %s" % (host['host_id'], host['url'])
        print "---------------------------------------------------------------"
        print "\n"
        resp_results.put(resp)


if __name__ == "__main__":
    usage = "usage: %prog [options]"
    parser = OptionParser(usage)

    parser.add_option("-d", "--csv-dir", dest="csv_dir",
                      help="The directory of CSV files used for depolyment")
    parser.add_option("-u", "--compass-url", dest="compass_url",
                      help="The URL of Compass server")
    (options, args) = parser.parse_args()

    if not os.exists(options.csv_dir):
        print "Cannot find the directory: %s" % options.csv_dir

    start(options.csv_dir, options.compass_url)
