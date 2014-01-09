"""Define all the RestfulAPI entry points"""
import logging
import simplejson as json
from flask import request
from flask.ext.restful import Resource
from sqlalchemy.sql import and_, or_

from compass.api import app, util, errors
from compass.tasks.client import celery
from compass.db import database
from compass.db.model import Switch as ModelSwitch
from compass.db.model import Machine as ModelMachine
from compass.db.model import Cluster as ModelCluster
from compass.db.model import ClusterHost as ModelClusterHost
from compass.db.model import Adapter
from compass.db.model import Role


class SwitchList(Resource):
    """Query detals of switches and poll swithes"""

    ENDPOINT = "/switches"

    SWITCHIP = 'switchIp'
    SWITCHIPNETWORK = 'switchIpNetwork'
    LIMIT = 'limit'

    def get(self):
        """
        List details of all switches, optionally filtered by some conditions.
        Note: switchIp and swtichIpNetwork cannot be combined to use.

        :param switchIp: switch IP address
        :param switchIpNetwork: switch IP network
        :param limit: the number of records excepted to return
        """
        qkeys = request.args.keys()
        logging.info('SwitchList query strings : %s', qkeys)
        switch_list = []

        with database.session() as session:
            switches = []
            switch_ips = request.args.getlist(self.SWITCHIP)
            switch_ip_network = request.args.get(self.SWITCHIPNETWORK,
                                                 type=str)
            limit = request.args.get(self.LIMIT, 0, type=int)

            if switch_ips and switch_ip_network:
                error_msg = 'switchIp and switchIpNetwork cannot be combined!'
                return errors.handle_invalid_usage(
                    errors.UserInvalidUsage(error_msg))

            if limit < 0:
                error_msg = "limit cannot be less than 1!"
                return errors.handle_invalid_usage(
                    errors.UserInvalidUsage(error_msg))

            if switch_ips:
                for ip_addr in switch_ips:
                    ip_addr = str(ip_addr)
                    if not util.is_valid_ip(ip_addr):
                        error_msg = 'SwitchIp format is incorrect!'
                        return errors.handle_invalid_usage(
                            errors.UserInvalidUsage(error_msg))
                    switch = session.query(ModelSwitch).filter_by(ip=ip_addr)\
                                                       .first()
                    if switch:
                        switches.append(switch)
                        logging.info('[SwitchList][get] ip %s', ip_addr)

            elif switch_ip_network:
                # query all switches which belong to the same network
                if not util.is_valid_ipnetowrk(switch_ip_network):
                    error_msg = 'SwitchIpNetwork format is incorrect!'
                    return errors.handle_invalid_usage(
                        errors.UserInvalidUsage(error_msg))

                def get_queried_ip_prefix(network, prefix):
                    """ Get Ip prefex as pattern used to query switches.
                        Switches' Ip addresses need to match this pattern.
                    """
                    count = int(prefix/8)
                    if count == 0:
                        count = 1
                    return network.rsplit('.', count)[0]+'.'

                from netaddr import IPNetwork, IPAddress

                ip_network = IPNetwork(switch_ip_network)
                ip_filter = get_queried_ip_prefix(str(ip_network.network),
                                                  ip_network.prefixlen)

                logging.info('ip_filter is %s', ip_filter)
                result_set = session.query(ModelSwitch).filter(
                    ModelSwitch.ip.startswith(ip_filter)).all()

                for switch in result_set:
                    ip_addr = str(switch.ip)
                    if IPAddress(ip_addr) in ip_network:
                        switches.append(switch)
                        logging.info('[SwitchList][get] ip %s', ip_addr)

                if limit and len(switches) > limit:
                    switches = switches[:limit]

            elif limit and not switches:
                switches = session.query(ModelSwitch).limit(limit).all()
            else:
                switches = session.query(ModelSwitch).all()

            for switch in switches:
                switch_res = {}
                switch_res['id'] = switch.id
                switch_res['ip'] = switch.ip
                switch_res['state'] = switch.state
                switch_res['link'] = {
                    'rel': 'self',
                    'href': '/'.join((self.ENDPOINT, str(switch.id)))}
                switch_list.append(switch_res)
        logging.info('get switch list: %s', switch_list)

        return util.make_json_response(
            200, {"status": 'OK',
                  "switches": switch_list})

    def post(self):
        """
        Insert switch IP and the credential to db. Invoke a task to poll
        switch at the same time.

        :param ip: switch IP address
        :param credential: a dict for accessing the switch
        """
        ip_addr = None
        credential = None
        logging.debug('post switch request from curl is %s', request.data)
        json_data = json.loads(request.data)
        ip_addr = json_data['switch']['ip']
        credential = json_data['switch']['credential']

        logging.info('post switch ip_addr=%s credential=%s(%s)',
                     ip_addr, credential, type(credential))

        if not util.is_valid_ip(ip_addr):
            error_msg = "Invalid IP address format!"
            return errors.handle_invalid_usage(
                errors.UserInvalidUsage(error_msg)
                )

        new_switch = {}
        with database.session() as session:
            switch = session.query(ModelSwitch).filter_by(ip=ip_addr).first()
            logging.info('switch for ip %s: %s', ip_addr, switch)

            if switch:
                error_msg = "IP address '%s' already exists" % ip_addr
                value = {'failedSwitch': switch.id}
                return errors.handle_duplicate_object(
                    errors.ObjectDuplicateError(error_msg), value
                )

            switch = ModelSwitch(ip=ip_addr)
            switch.credential = credential
            session.add(switch)
            session.flush()
            new_switch['id'] = switch.id
            new_switch['ip'] = switch.ip
            new_switch['state'] = switch.state
            link = {'rel': 'self',
                    'href': '/'.join((self.ENDPOINT, str(switch.id)))}
            new_switch['link'] = link

        celery.send_task("compass.tasks.pollswitch", (ip_addr,))
        logging.info('new switch added: %s', new_switch)
        return util.make_json_response(
            202, {"status": "accepted",
                  "switch":  new_switch}
            )


class Switch(Resource):
    """Get and update a single switch information"""
    ENDPOINT = "/switches"

    def get(self, switch_id):
        """Lists details of the specified switch.

        :param switch_id: switch ID in db
        """
        switch_res = {}
        with database.session() as session:
            switch = session.query(ModelSwitch).filter_by(id=switch_id).first()
            logging.info('switch for id %s: %s', switch_id, switch)

            if not switch:
                error_msg = "Cannot find the switch with id=%s" % switch_id
                logging.error("[/switches/{id}]error_msg: %s", error_msg)

                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg)
                    )

            switch_res['id'] = switch.id
            switch_res['ip'] = switch.ip
            switch_res['state'] = switch.state
            switch_res['link'] = {
                'rel': 'self',
                'href': '/'.join((self.ENDPOINT, str(switch.id)))}

        logging.info('switch info for %s: %s', switch_id, switch_res)
        return util.make_json_response(
            200, {"status": "OK",
                  "switch": switch_res})

    def put(self, switch_id):
        """Update an existing switch information.

        :param switch_id: the unqiue identifier of the switch
        """
        switch = None
        with database.session() as session:
            switch = session.query(ModelSwitch).filter_by(id=switch_id).first()
            logging.info('PUT switch id is %s: %s', switch_id, switch)

            if not switch:
                # No switch is found.
                error_msg = 'Cannot update a non-existing switch!'
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg))

        credential = None
        logging.debug('PUT a switch request from curl is %s', request.data)
        json_data = json.loads(request.data)
        credential = json_data['switch']['credential']

        logging.info('PUT switch id=%s credential=%s(%s)',
                     switch_id, credential, type(credential))
        ip_addr = None
        switch_res = {}
        with database.session() as session:
            switch = session.query(ModelSwitch).filter_by(id=switch_id).first()
            switch.credential = credential
            switch.state = "not_reached"

            ip_addr = switch.ip
            switch_res['id'] = switch.id
            switch_res['ip'] = switch.ip
            switch_res['state'] = switch.state
            link = {'rel': 'self',
                    'href': '/'.join((self.ENDPOINT, str(switch.id)))}
            switch_res['link'] = link

        celery.send_task("compass.tasks.pollswitch", (ip_addr,))
        return util.make_json_response(
            202, {"status": "accepted",
                  "switch": switch_res})

    def delete(self, switch_id):
        """No implementation.

        :param switch_id: the unique identifier of the switch.
        """
        return errors.handle_not_allowed_method(
            errors.MethodNotAllowed())


class MachineList(Resource):
    """Query machines by filters"""
    ENDPOINT = "/machines"

    SWITCHID = 'switchId'
    VLANID = 'vladId'
    PORT = 'port'
    LIMIT = 'limit'

    def get(self):
        """
        Lists details of machines, optionally filtered by some conditions as
        the following.

        :param switchId: the unique identifier of the switch
        :param vladId: the vlan ID
        :param port: the port number
        :param limit: the number of records expected to return
        """
        machines_result = []
        switch_id = request.args.get(self.SWITCHID, type=int)
        vlan = request.args.get(self.VLANID, type=int)
        port = request.args.get(self.PORT, type=int)
        limit = request.args.get(self.LIMIT, 0, type=int)

        with database.session() as session:
            machines = []
            filter_clause = []
            if switch_id:
                filter_clause.append('switch_id=%d' % switch_id)

            if vlan:
                filter_clause.append('vlan=%d' % vlan)

            if port:
                filter_clause.append('port=%d' % port)

            if limit < 0:
                error_msg = 'Limit cannot be less than 0!'
                return errors.UserInvalidUsage(
                    errors.UserInvalidUsage(error_msg)
                )

            if filter_clause:
                if limit:
                    machines = session.query(ModelMachine)\
                                      .filter(and_(*filter_clause))\
                                      .limit(limit).all()
                else:
                    machines = session.query(ModelMachine)\
                                      .filter(and_(*filter_clause)).all()
            else:
                if limit:
                    machines = session.query(ModelMachine).limit(limit).all()
                else:
                    machines = session.query(ModelMachine).all()

            logging.info('all machines: %s', machines)
            for machine in machines:
                machine_res = {}
                machine_res['switch_ip'] = None if not machine.switch else \
                    machine.switch.ip
                machine_res['id'] = machine.id
                machine_res['mac'] = machine.mac
                machine_res['port'] = machine.port
                machine_res['vlan'] = machine.vlan
                machine_res['link'] = {
                    'rel': 'self',
                    'href': '/'.join((self.ENDPOINT, str(machine.id)))}
                machines_result.append(machine_res)

        logging.info('machines for %s: %s', switch_id, machines_result)
        return util.make_json_response(
            200, {"status": "OK",
                  "machines": machines_result})


class Machine(Resource):
    """List details of the machine with specific machine id"""
    ENDPOINT = '/machines'

    def get(self, machine_id):
        """
        Lists details of the specified machine.

        :param machine_id: the unique identifier of the machine
        """
        machine_res = {}
        with database.session() as session:
            machine = session.query(ModelMachine)\
                             .filter_by(id=machine_id)\
                             .first()
            logging.info('machine for id %s: %s', machine_id, machine)

            if not machine:
                error_msg = "Cannot find the machine with id=%s" % machine_id
                logging.error("[/api/machines/{id}]error_msg: %s", error_msg)

                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg))

            machine_res['id'] = machine.id
            machine_res['mac'] = machine.mac
            machine_res['port'] = machine.port
            machine_res['vlan'] = machine.vlan
            if machine.switch:
                machine_res['switch_ip'] = machine.switch.ip
            else:
                machine_res['switch_ip'] = None
            machine_res['link'] = {
                'rel': 'self',
                'href': '/'.join((self.ENDPOINT, str(machine.id)))}

        logging.info('machine info for %s: %s', machine_id, machine_res)
        return util.make_json_response(
            200, {"status": "OK",
                  "machine": machine_res})


class Cluster(Resource):
    """Creates cluster and lists cluster details; Update and list the cluster's
       configuration information.
    """
    ENDPOINT = '/clusters'
    SECURITY = 'security'
    NETWORKING = 'networking'
    PARTITION = 'partition'

    def get(self, cluster_id, resource=None):
        """
        Lists details of the specified cluster if resource is not specified.
        Otherwise, lists details of the resource of this cluster

        :param cluster_id: the unique identifier of the cluster
        :param resource: the resource name(security, networking, partition)
        """
        cluster_resp = {}
        resp = {}
        with database.session() as session:
            cluster = session.query(ModelCluster)\
                             .filter_by(id=cluster_id)\
                             .first()
            logging.debug('cluster is %s', cluster)
            if not cluster:
                error_msg = 'Cannot found the cluster with id=%s' % cluster_id
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg)
                    )

            if resource:
                # List resource details
                if resource == self.SECURITY:
                    cluster_resp = cluster.security
                elif resource == self.NETWORKING:
                    cluster_resp = cluster.networking
                elif resource == self.PARTITION:
                    cluster_resp = cluster.partition
                else:
                    error_msg = "Invalid resource name '%s'!" % resource
                    return errors.handle_invalid_usage(
                        errors.UserInvalidUsage(error_msg)
                    )
                resp = {"status": "OK",
                        resource: cluster_resp}

            else:
                cluster_resp['clusterName'] = cluster.name
                cluster_resp['link'] = {
                    'rel': 'self',
                    'href': '/'.join((self.ENDPOINT, str(cluster.id)))
                }
                cluster_resp['id'] = cluster.id
                resp = {"status": "OK",
                        "cluster": cluster_resp}

        logging.info('get cluster result is %s', cluster_resp)
        return util.make_json_response(200, resp)

    def post(self):
        """Create a new cluster.

        :param name: the name of the cluster
        :param adapter_id: the unique identifier of the adapter
        """
        request_data = None
        request_data = json.loads(request.data)
        cluster_name = request_data['cluster']['name']
        adapter_id = request_data['cluster']['adapter_id']
        cluster_resp = {}
        cluster = None

        with database.session() as session:
            cluster = session.query(ModelCluster).filter_by(name=cluster_name)\
                                                 .first()
            if cluster:
                error_msg = "Cluster name '%s' already exists!" % cluster.name
                return errors.handle_duplicate_object(
                    errors.ObjectDuplicateError(error_msg))

            # Create a new cluster in database
            cluster = ModelCluster(name=cluster_name, adapter_id=adapter_id)
            session.add(cluster)
            session.flush()
            cluster_resp['id'] = cluster.id
            cluster_resp['name'] = cluster.name
            cluster_resp['adapter_id'] = cluster.adapter_id
            cluster_resp['link'] = {
                'rel': 'self',
                'href': '/'.join((self.ENDPOINT, str(cluster.id)))
            }

        return util.make_json_response(
            200, {"status": "OK",
                  "cluster": cluster_resp}
            )

    def put(self, cluster_id, resource):
        """
        Update the resource information of the specified cluster in database

        :param cluster_id: the unique identifier of the cluster
        :param resource: resource name(security, networking, partition)
        """
        resources = {
            self.SECURITY: {'validator': 'is_valid_security_config',
                            'column': 'security_config'},
            self.NETWORKING: {'validator': 'is_valid_networking_config',
                              'column': 'networking_config'},
            self.PARTITION: {'validator': 'is_valid_partition_config',
                             'column': 'partition_config'},
        }
        request_data = json.loads(request.data)
        with database.session() as session:
            cluster = session.query(ModelCluster).filter_by(id=cluster_id)\
                                                 .first()

            if not cluster:
                error_msg = 'You are trying to update a non-existing cluster!'
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg)
                    )
            if resource not in request_data:
                error_msg = "Invalid resource name '%s'" % resource
                return errors.handle_invalid_usage(
                    errors.UserInvalidUsage(error_msg))

            value = request_data[resource]

            if resource not in resources.keys():
                error_msg = "Invalid resource name '%s'" % resource
                return errors.handle_invalid_usage(
                    errors.UserInvalidUsage(error_msg))

            validate_func = resources[resource]['validator']
            module = globals()['util']
            is_valid, msg = getattr(module, validate_func)(value)

            if is_valid:
                column = resources[resource]['column']
                session.query(ModelCluster).filter_by(id=cluster_id)\
                       .update({column: json.dumps(value)})
            else:
                return errors.handle_mssing_input(
                    errors.InputMissingError(msg))

        return util.make_json_response(
            200, {"status": "OK"})


@app.route("/clusters", methods=['GET'])
def list_clusters():
    """Lists the details of all clusters"""
    endpoint = '/clusters'
    results = []
    with database.session() as session:
        clusters = session.query(ModelCluster).all()

        if clusters:
            for cluster in clusters:
                cluster_res = {}
                cluster_res['clusterName'] = cluster.name
                cluster_res['id'] = cluster.id
                cluster_res['link'] = {
                    "href": "/".join((endpoint, str(cluster.id))),
                    "rel": "self"}
                results.append(cluster_res)

    return util.make_json_response(
        200, {"status": "OK",
              "clusters": results})


@app.route("/clusters/<string:cluster_id>/action", methods=['POST'])
def execute_cluster_action(cluster_id):
    """Execute the specified  action to the cluster.

    :param cluster_id: the unique identifier of the cluster
    :param addHosts: the action of adding excepted hosts to the cluster
    :param removeHosts: the action of removing expected hosts from the cluster
    :param replaceAllHosts: the action of removing all existing hosts in
                            cluster and add new hosts
    :param deploy: the action of starting to deploy
    """
    def _add_hosts(cluster_id, hosts):
        """Add cluster host(s) to the cluster by cluster_id"""

        cluseter_hosts = []
        available_machines = []
        failed_machines = []
        with database.session() as session:
            failed_machines = []
            for host in hosts:
                # Check if machine exists
                machine = session.query(ModelMachine).filter_by(id=host)\
                                                     .first()
                if not machine:
                    error_msg = "Machine id=%s does not exist!" % host
                    return errors.handle_not_exist(
                        errors.ObjectDoesNotExist(error_msg)
                        )
                clusterhost = session.query(ModelClusterHost)\
                                     .filter_by(machine_id=host)\
                                     .first()
                if clusterhost:
                    # Machine is already used
                    failed_machines.append(clusterhost.machine_id)
                    continue
                # Add the available machine to available_machines list
                available_machines.append(machine)

            if failed_machines:
                value = {
                    'failedMachines': failed_machines
                }
                error_msg = "Conflict!"
                return errors.handle_duplicate_object(
                    errors.ObjectDuplicateError(error_msg), value
                    )
            for machine, host in zip(available_machines, hosts):
                host = ModelClusterHost(cluster_id=cluster_id,
                                        machine_id=machine.id)
                session.add(host)
                session.flush()
                cluster_res = {}
                cluster_res['id'] = host.id
                cluster_res['machine_id'] = machine.id
                cluseter_hosts.append(cluster_res)

        logging.info('cluster_hosts result is %s', cluseter_hosts)
        return util.make_json_response(
            200, {
                "status": "OK",
                "cluster_hosts": cluseter_hosts
                }
            )

    def _remove_hosts(cluster_id, hosts):
        """Remove existing cluster host from the cluster"""

        removed_hosts = []
        with database.session() as session:
            failed_hosts = []
            for host_id in hosts:
                host = session.query(ModelClusterHost).filter_by(id=host_id)\
                                                      .first()

                if not host:
                    failed_hosts.append(host)
                    continue

                host_res = {
                    "id": host_id,
                    "machine_id": host.machine_id
                }
                removed_hosts.append(host_res)

            if failed_hosts:
                error_msg = 'Cluster hosts do not exist!'
                value = {
                    "failedHosts": failed_hosts
                }
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg), value
                    )

            filter_clause = []
            for host_id in hosts:
                filter_clause.append('id=%s' % host_id)

            # Delete the requested hosts from database
            session.query(ModelClusterHost).filter(or_(*filter_clause))\
                   .delete(synchronize_session='fetch')

        return util.make_json_response(
            200, {
                "status": "OK",
                "cluster_hosts": removed_hosts
                }
            )

    def _replace_all_hosts(cluster_id, hosts):
        """Remove all existing hosts from the cluster and add new ones"""

        with database.session() as session:
            # Delete all existing hosts of the cluster
            session.query(ModelClusterHost)\
                   .filter_by(cluster_id=cluster_id).delete()
            session.flush()
        return _add_hosts(cluster_id, hosts)

    def _deploy(cluster_id):
        """Deploy the cluster"""

        deploy_hosts_urls = []
        with database.session() as session:
            cluster_hosts_ids = session.query(ModelClusterHost.id)\
                                       .filter_by(cluster_id=cluster_id).all()
            if not cluster_hosts_ids:
                # No host belongs to this cluster
                error_msg = ('Cannot find any host in cluster id=%s' %
                             cluster_id)
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg))

            for elm in cluster_hosts_ids:
                host_id = str(elm[0])
                progress_url = '/cluster_hosts/%s/progress' % host_id
                deploy_hosts_urls.append(progress_url)

            # Lock cluster hosts and its cluster
            session.query(ModelClusterHost).filter_by(cluster_id=cluster_id)\
                                           .update({'mutable': False})
            session.query(ModelCluster).filter_by(id=cluster_id)\
                                       .update({'mutable': False})

        celery.send_task("compass.tasks.trigger_install", (cluster_id,))
        return util.make_json_response(
            202, {"status": "OK",
                  "deployment": deploy_hosts_urls})

    request_data = None
    with database.session() as session:
        cluster = session.query(ModelCluster).filter_by(id=cluster_id).first()
        if not cluster:
            error_msg = 'Cluster id=%s does not exist!'
            return errors.handle_not_exist(
                errors.ObjectDoesNotExist(error_msg)
                )
        if not cluster.mutable:
            # The cluster cannot be deploy again
            error_msg = "The cluster id=%s cannot deploy again!" % cluster_id
            return errors.handle_invalid_usage(
                errors.UserInvalidUsage(error_msg))

    request_data = json.loads(request.data)
    action = request_data.keys()[0]
    value = request_data.get(action)

    if 'addHosts' in request_data:
        return _add_hosts(cluster_id, value)

    elif 'removeHosts' in request_data:
        return _remove_hosts(cluster_id, value)

    elif 'deploy' in request_data:
        return _deploy(cluster_id)

    elif 'replaceAllHosts' in request_data:
        return _replace_all_hosts(cluster_id, value)
    else:
        return errors.handle_invalid_usage(
            errors.UserInvalidUsage('%s action is not support!' % action)
            )


class ClusterHostConfig(Resource):
    """Lists and update/delete cluster host configurations"""

    def get(self, host_id):
        """Lists configuration details of the specified cluster host

        :param host_id: the unique identifier of the host
        """
        config_res = {}
        with database.session() as session:
            host = session.query(ModelClusterHost).filter_by(id=host_id)\
                                                  .first()
            if not host:
                # The host does not exist.
                error_msg = "The host id=%s does not exist!" % host_id
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg))

            config_res = host.config

        logging.debug("The config of host id=%s is %s", host_id, config_res)
        return util.make_json_response(
            200, {"status": "OK",
                  "config": config_res})

    def put(self, host_id):
        """
        Update configuration of the specified cluster host

        :param host_id: the unique identifier of the host
        """
        with database.session() as session:
            host = session.query(ModelClusterHost).filter_by(id=host_id)\
                                                  .first()
            if not host:
                error_msg = "The host id=%s does not exist!" % host_id
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg))
            logging.debug("cluster config put request.data %s", request.data)
            request_data = json.loads(request.data)
            if not request_data:
                error_msg = "request data is %s" % request_data
                return errors.handle_mssing_input(
                    errors.InputMissingError(error_msg))

            if not host.mutable:
                error_msg = "The host 'id=%s' is not mutable!" % host_id
                return errors.handle_invalid_usage(
                    errors.UserInvalidUsage(error_msg))

            #Valid if keywords in request_data are all correct
            if 'hostname' in request_data:
                session.query(ModelClusterHost).filter_by(id=host_id)\
                       .update({"hostname": request_data['hostname']})
                del request_data['hostname']

            try:
                util.valid_host_config(request_data)
            except errors.UserInvalidUsage as exc:
                return errors.handle_invalid_usage(exc)

            host.config = request_data

            return util.make_json_response(
                200, {"status": "OK"})

    def delete(self, host_id, subkey):
        """
        Delete one attribute in configuration of the specified cluster host

        :param host_id: the unique identifier of the host
        :param subkey: the attribute name in configuration
        """
        available_delete_keys = ['ip', 'roles']
        with database.session() as session:
            host = session.query(ModelClusterHost).filter_by(id=host_id)\
                                                  .first()
            if not host:
                error_msg = "The host id=%s does not exist!" % host_id
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg))

            if subkey not in available_delete_keys:
                error_msg = "subkey %s is not supported!" % subkey
                return errors.handle_invalid_usage(
                    errors.UserInvalidUsage(error_msg))

            if not host.mutable:
                error_msg = "The host 'id=%s' is not mutable!" % host_id
                return errors.handle_invalid_usage(
                    errors.UserInvalidUsage(error_msg))

            config = json.loads(host.config_data)
            # Set the subkey's value to ""
            util.update_dict_value(subkey, "", config)
            host.config = config

        return util.make_json_response(
            200, {"status": "OK"})


class ClusterHost(Resource):
    """List details of the cluster host by host id"""
    ENDPOINT = '/clusterhosts'

    def get(self, host_id):
        """Lists details of the specified cluster host

        :param host_id: the unique identifier of the host
        """
        host_res = {}
        with database.session() as session:
            host = session.query(ModelClusterHost).filter_by(id=host_id)\
                                                  .first()
            if not host:
                error_msg = "The host id=%s does not exist!" % host_id
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg))
            host_res['hostname'] = host.hostname
            host_res['mutable'] = host.mutable
            host_res['id'] = host.id
            host_res['link'] = {
                "href": '/'.join((self.ENDPOINT, str(host.id))),
                "rel": "self"
            }
        return util.make_json_response(
            200, {"status": "OK",
                  "cluster_host": host_res})


@app.route("/clusterhosts", methods=['GET'])
def list_clusterhosts():
    """
    Lists details of all cluster hosts, optionally filtered by some conditions.

    :param hostname: the name of the host
    :param clstername: the name of the cluster
    """
    endpoint = '/clusterhosts'
    key_hostname = 'hostname'
    key_clustername = 'clustername'

    hosts_list = []
    hostname = request.args.get(key_hostname, None, type=str)
    clustername = request.args.get(key_clustername, None, type=str)
    with database.session() as session:
        hosts = None
        if hostname and clustername:
            hosts = session.query(ModelClusterHost).join(ModelCluster)\
                           .filter(ModelClusterHost.hostname == hostname,
                                   ModelCluster.name == clustername)\
                           .all()

        elif hostname:
            hosts = session.query(ModelClusterHost)\
                           .filter_by(hostname=hostname).all()
        elif clustername:
            cluster = session.query(ModelCluster)\
                             .filter_by(name=clustername).first()
            if cluster:
                hosts = cluster.hosts
        else:
            hosts = session.query(ModelClusterHost).all()

        if hosts:
            for host in hosts:
                host_res = {}
                host_res['hostname'] = host.hostname
                host_res['mutable'] = host.mutable
                host_res['id'] = host.id
                host_res['link'] = {
                    "href": '/'.join((endpoint, str(host.id))),
                    "rel": "self"}
                hosts_list.append(host_res)

        return util.make_json_response(
            200, {"status": "OK",
                  "cluster_hosts": hosts_list})


@app.route("/adapters/<string:adapter_id>", methods=['GET'])
def list_adapter(adapter_id):
    """
    Lists details of the specified adapter.

    :param adapter_id: the unique identifier of the adapter
    """
    endpoint = '/adapters'
    adapter_res = {}
    with database.session() as session:
        adapter = session.query(Adapter).filter_by(id=adapter_id).first()

        if not adapter:
            error_msg = "Adapter id=%s does not exist!" % adapter_id
            return errors.handle_not_exist(
                errors.ObjectDoesNotExist(error_msg))
        adapter_res['name'] = adapter.name
        adapter_res['os'] = adapter.os
        adapter_res['id'] = adapter.id
        adapter_res['target_system'] = adapter.target_system,
        adapter_res['link'] = {
            "href": "/".join((endpoint, str(adapter.id))),
            "rel": "self"}
    return util.make_json_response(
        200, {"status": "OK",
              "adapter": adapter_res})


@app.route("/adapters/<string:adapter_id>/roles", methods=['GET'])
def list_adapter_roles(adapter_id):
    """Lists details of all roles of the specified adapter

    :param adapter_id: the unique identifier of the adapter
    """
    roles_list = []
    with database.session() as session:
        adapter_q = session.query(Adapter)\
                           .filter_by(id=adapter_id).first()
        if not adapter_q:
            error_msg = "Adapter id=%s does not exist!" % adapter_id
            return errors.handle_not_exist(
                errors.ObjectDoesNotExist(error_msg))

        roles = session.query(Role, Adapter)\
                       .filter(Adapter.id == adapter_id,
                               Adapter.target_system == Role.target_system)\
                       .all()

        for role, adapter in roles:
            role_res = {}
            role_res['name'] = role.name
            role_res['description'] = role.description
            roles_list.append(role_res)

    return util.make_json_response(
        200, {"status": "OK",
              "roles": roles_list})


@app.route("/adapters", methods=['GET'])
def list_adapters():
    """Lists details of the adapters, optionally filtered by adapter name.

    :param name: the name of the adapter
    """
    endpoint = '/adapters'
    name = request.args.get('name', type=str)
    adapter_list = []
    adapter_res = {}
    with database.session() as session:
        adapters = []
        if name:
            adapters = session.query(Adapter).filter_by(name=name).all()
        else:
            adapters = session.query(Adapter).all()

        for adapter in adapters:
            adapter_res = {}
            adapter_res['name'] = adapter.name
            adapter_res['os'] = adapter.os
            adapter_res['target_system'] = adapter.target_system
            adapter_res['id'] = adapter.id
            adapter_res['link'] = {
                "href": "/".join((endpoint, str(adapter.id))),
                "rel": "self"}
            adapter_list.append(adapter_res)

    return util.make_json_response(
        200, {"status": "OK",
              "adapters": adapter_list})


class HostInstallingProgress(Resource):
    """Get host installing progress information"""

    def get(self, host_id):
        """Lists progress details of a specific cluster host

        :param host_id: the unique identifier of the host
        """
        progress_result = {}
        with database.session() as session:
            host = session.query(ModelClusterHost).filter_by(id=host_id)\
                                                  .first()
            if not host:
                error_msg = "The host id=%s does not exist!" % host_id
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg))

            if not host.state:
                progress_result = {
                    'id': host_id,
                    'state': 'UNINITIALIZED',
                    'percentage': 0,
                    'message': "Waiting..............",
                    'severity': "INFO",
                }
            else:
                progress_result['id'] = host_id
                progress_result['state'] = host.state.state
                progress_result['percentage'] = host.state.progress
                progress_result['message'] = host.state.message
                progress_result['severity'] = host.state.severity

        logging.info('progress result for %s: %s', host_id, progress_result)
        return util.make_json_response(
            200, {"status": "OK",
                  "progress": progress_result})


class ClusterInstallingProgress(Resource):
    """Get cluster installing progress information"""

    def get(self, cluster_id):
        """Lists progress details of a specific cluster

        :param cluster_id: the unique identifier of the cluster
        """
        progress_result = {}
        with database.session() as session:
            cluster = session.query(ModelCluster).filter_by(id=cluster_id)\
                                                 .first()
            if not cluster:
                error_msg = "The cluster id=%s does not exist!" % cluster_id
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg))

            if not cluster.state:
                progress_result = {
                    'id': cluster_id,
                    'state': 'UNINITIALIZED',
                    'percentage': 0,
                    'message': "Waiting..............",
                    'severity': "INFO"
                }
            else:
                progress_result['id'] = cluster_id
                progress_result['state'] = cluster.state.state
                progress_result['percentage'] = cluster.state.progress
                progress_result['message'] = cluster.state.message
                progress_result['severity'] = cluster.state.severity

        logging.info('progress result for cluster %s: %s',
                     cluster_id, progress_result)
        return util.make_json_response(
            200, {"status": "OK",
                  "progress": progress_result})


class DashboardLinks(Resource):
    """Lists dashboard links"""
    ENDPOINT = "/dashboardlinks/"

    def get(self):
        """
        Return a list of dashboard links
        """
        cluster_id = request.args.get('cluster_id', None)
        logging.info('get cluster links with cluster_id=%s', cluster_id)
        links = {}
        with database.session() as session:
            hosts = session.query(ModelClusterHost)\
                           .filter_by(cluster_id=cluster_id).all()
            if not hosts:
                error_msg = "Cannot find hosts in cluster id=%s" % cluster_id
                return errors.handle_not_exist(
                    errors.ObjectDoesNotExist(error_msg))

            for host in hosts:
                config = host.config
                if ('has_dashboard_roles' in config and
                        config['has_dashboard_roles']):
                    ip = config.get(
                        'networking', {}).get(
                        'interfaces', {}).get(
                        'management', {}).get(
                        'ip', '')
                    roles = config.get('roles', [])
                    for role in roles:
                        links[role] = 'http://%s' % ip

        return util.make_json_response(
            200, {"status": "OK",
                  "dashboardlinks": links}
            )


util.add_resource(SwitchList, '/switches')
util.add_resource(Switch, '/switches/<string:switch_id>')
util.add_resource(MachineList, '/machines')
util.add_resource(Machine, '/machines/<string:machine_id>')
util.add_resource(Cluster,
                  '/clusters',
                  '/clusters/<string:cluster_id>',
                  '/clusters/<string:cluster_id>/<string:resource>')
util.add_resource(ClusterHostConfig,
                  '/clusterhosts/<string:host_id>/config',
                  '/clusterhosts/<string:host_id>/config/<string:subkey>')
util.add_resource(ClusterHost, '/clusterhosts/<string:host_id>')
util.add_resource(HostInstallingProgress,
                  '/clusterhosts/<string:host_id>/progress')
util.add_resource(ClusterInstallingProgress,
                  '/clusters/<string:cluster_id>/progress')
util.add_resource(DashboardLinks, '/dashboardlinks')

if __name__ == '__main__':
    app.run(debug=True)
