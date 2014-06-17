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
from compass.hdsdiscovery.hdmanager import HDManager


def _poll_switch(ip_addr, credentials, req_obj='mac', oper="SCAN"):
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

    state = under_monitoring
    machine_dicts = {}
    for machine in results:
        mac = machine['mac']
        port = machine['port']
        vlan = machine['vlan']
        if vlan:
            vlans = [vlan]
        else:
            vlans = []
        if mac not in machine_dicts:
            machine_dicts[mac] = {'port': port, 'vlans': vlans}
        else:
            machine_dicts[mac]['port'] = port
            machine_dicts[mac]['vlans'].extend(vlans)

    logging.debug('update switch %s state to under monitoring', ip_addr)
    return (
        {'vendor': vendor, 'state': state, 'err_msg': err_msg},
        machine_dicts
    )


def poll_switch(ip_addr, credentials, req_obj='mac', oper="SCAN"):
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
    with util.lock('poll switch %s' % ip_addr) as lock:
        if not lock:
            raise Exception(
                'failed to acquire lock to poll switch %s' % ip_addr
            )

        logging.debug('poll switch: %s', ip_addr)
        ip_int = long(netaddr.IPAddress(ip_addr))
        switch_dict, machine_dicts = _poll_switch(
            ip_addr, credentials, req_obj=req_obj, oper=oper
        )
        with database.session() as session:
            switch = switch_api.get_switch_internal(
                session, False, ip_int=ip_int
            )
            if not switch:
                logging.error('no switch found for %s', ip_addr)
                return

            switch_api.update_switch_internal(
                session, switch, **switch_dict
            )
            switch_api.add_switch_machines_internal(
                session, switch, machine_dicts, False
            )
