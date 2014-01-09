"""Module to provider function to poll switch."""
import logging

from compass.db import database
from compass.db.model import Switch, Machine
from compass.hdsdiscovery.hdmanager import HDManager


def poll_switch(ip_addr, req_obj='mac', oper="SCAN"):
    """Query switch and return expected result

    .. note::
       When polling switch succeeds, for each mac it got from polling switch,
       A Machine record associated with the switch is added to the database.

    :param ip_addr: switch ip address.
    :type ip_addr: str
    :param req_obj: the object requested to query from switch.
    :type req_obj: str
    :param oper: the operation to query the switch.
    :type oper: str, should be one of ['SCAN', 'GET', 'SET']

    .. note::
       The function should be called inside database session scope.

    """
    if not ip_addr:
        logging.error('No switch IP address is provided!')
        return

    #Retrieve vendor info from switch table
    session = database.current_session()
    switch = session.query(Switch).filter_by(ip=ip_addr).first()
    logging.info("pollswitch: %s", switch)
    if not switch:
        logging.error('no switch found for %s', ip_addr)
        return

    credential = switch.credential
    logging.error("pollswitch: credential %r", credential)
    vendor = switch.vendor
    hdmanager = HDManager()

    if not vendor or not hdmanager.is_valid_vendor(ip_addr,
                                                   credential, vendor):
        # No vendor found or vendor doesn't match queried switch.
        logging.debug('no vendor or vendor had been changed for switch %s',
                      switch)
        vendor = hdmanager.get_vendor(ip_addr, credential)
        logging.debug('[pollswitch] credential %r', credential)
        if not vendor:
            logging.error('no vendor found or match switch %s', switch)
            return
        switch.vendor = vendor

    # Start to poll switch's mac address.....
    logging.debug('hdmanager learn switch from %s %s %s %s %s',
                  ip_addr, credential, vendor, req_obj, oper)
    results = hdmanager.learn(ip_addr, credential, vendor, req_obj, oper)
    logging.info("pollswitch %s result: %s", switch, results)
    if not results:
        logging.error('no result learned from %s %s %s %s %s',
                      ip_addr, credential, vendor, req_obj, oper)
        return

    for entry in results:
        mac = entry['mac']
        machine = session.query(Machine).filter_by(mac=mac).first()
        if not machine:
            machine = Machine(mac=mac)
            machine.port = entry['port']
            machine.vlan = entry['vlan']
            machine.switch = switch

    logging.debug('update switch %s state to under monitoring', switch)
    switch.state = 'under_monitoring'
