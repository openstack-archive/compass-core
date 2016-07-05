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

"""Module to provider function to poll switch."""
import logging
import netaddr

from compass.actions import util
from compass.db.api import database
from compass.db.api import switch as switch_api
from compass.db.api import user as user_api
from compass.hdsdiscovery.hdmanager import HDManager


def _poll_switch(ip_addr, credentials, req_obj='mac', oper="SCAN"):
    """Poll switch by ip addr.


    Args:
       ip_addr: ip addr of the switch.
       credentials: credentials of the switch.

    Returns: switch attributes dict and list of machine attributes dict.
    """
    under_monitoring = 'under_monitoring'
    unreachable = 'unreachable'
    polling_error = 'error'
    hdmanager = HDManager()
    vendor, state, err_msg = hdmanager.get_vendor(ip_addr, credentials)
    if not vendor:
        logging.info("*****error_msg: %s****", err_msg)
        logging.error('no vendor found or match switch %s', ip_addr)
        return (
            {
                'vendor': vendor, 'state': state, 'err_msg': err_msg
            }, {
            }
        )

    logging.debug(
        'hdmanager learn switch from %s', ip_addr
    )
    results = []
    try:
        results = hdmanager.learn(
            ip_addr, credentials, vendor, req_obj, oper
        )
    except Exception as error:
        logging.exception(error)
        state = unreachable
        err_msg = (
            'SNMP walk for querying MAC addresses timedout'
        )
        return (
            {
                'vendor': vendor, 'state': state, 'err_msg': err_msg
            }, {
            }
        )

    logging.info("pollswitch %s result: %s", ip_addr, results)
    if not results:
        logging.error(
            'no result learned from %s', ip_addr
        )
        state = polling_error
        err_msg = 'No result learned from SNMP walk'
        return (
            {'vendor': vendor, 'state': state, 'err_msg': err_msg},
            {}
        )

    logging.info('poll switch result: %s' % str(results))
    machine_dicts = {}
    for machine in results:
        mac = machine['mac']
        port = machine['port']
        vlan = int(machine['vlan'])
        if vlan:
            vlans = [vlan]
        else:
            vlans = []
        if mac not in machine_dicts:
            machine_dicts[mac] = {'mac': mac, 'port': port, 'vlans': vlans}
        else:
            machine_dicts[mac]['port'] = port
            machine_dicts[mac]['vlans'].extend(vlans)

    logging.debug('update switch %s state to under monitoring', ip_addr)
    state = under_monitoring
    return (
        {'vendor': vendor, 'state': state, 'err_msg': err_msg},
        machine_dicts.values()
    )


def poll_switch(poller_email, ip_addr, credentials,
                req_obj='mac', oper="SCAN"):
    """Query switch and update switch machines.

    .. note::
       When polling switch succeeds, for each mac it got from polling switch,
       A Machine record associated with the switch is added to the database.

    :param ip_addr: switch ip address.
    :type ip_addr: str
    :param credentials: switch crednetials.
    :type credentials: dict
    :param req_obj: the object requested to query from switch.
    :type req_obj: str
    :param oper: the operation to query the switch.
    :type oper: str, should be one of ['SCAN', 'GET', 'SET']

    .. note::
       The function should be called out of database session scope.
    """
    poller = user_api.get_user_object(poller_email)
    ip_int = long(netaddr.IPAddress(ip_addr))
    with util.lock('poll switch %s' % ip_addr, timeout=120) as lock:
        if not lock:
            raise Exception(
                'failed to acquire lock to poll switch %s' % ip_addr
            )

        # TODO(grace): before repoll the switch, set the state to repolling.
        # and when the poll switch is timeout, set the state to error.
        # the frontend should only consider some main state like INTIALIZED,
        # ERROR and SUCCESSFUL, REPOLLING is as an intermediate state to
        # indicate the switch is in learning the mac of the machines connected
        # to it.
        logging.debug('poll switch: %s', ip_addr)
        switch_dict, machine_dicts = _poll_switch(
            ip_addr, credentials, req_obj=req_obj, oper=oper
        )
        switches = switch_api.list_switches(ip_int=ip_int, user=poller)
        if not switches:
            logging.error('no switch found for %s', ip_addr)
            return

        for switch in switches:
            for machine_dict in machine_dicts:
                logging.info('add machine: %s', machine_dict)
                machine_dict['owner_id'] = poller.id
                switch_api.add_switch_machine(
                    switch['id'], False, user=poller, **machine_dict
                )
                switch_api.update_switch(
                    switch['id'],
                    user=poller,
                    **switch_dict
                )
