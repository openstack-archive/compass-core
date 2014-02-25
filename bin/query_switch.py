#!/usr/bin/python
import os
import threading
import time

from Queue import Queue, Empty
from optparse import OptionParser

from compass.apiclient.restful import Client


class AddSwitch(object):
    """ A utility class that handles adding a switch and retrieving
        corresponding machines associated with the switch. """

    def __init__(self, server_url):
        print server_url, " ...."
        self._client = Client(server_url)

    def add_switch(self, queue, ip, snmp_community):
        """ Add a switch with SNMP credentials and retrieve attached
            server machines.

        :param queue: The result holder for the machine details.
        :type queue: A Queue object(thread-safe).
        :param ip: The IP address of the switch.
        :type ip: string.
        :param snmp_community: The SNMP community string.
        :type snmp_community: string.
        """
        status, resp = self._client.add_switch(ip,
                                               version="2c",
                                               community=snmp_community)
        if status > 409:
            queue.put((ip, (False,
                            "Failed to add the switch (status=%d)" % status)))
            return

        if status == 409:
            switch_id = resp['failedSwitch']
            status, resp = self._client.update_switch(switch_id,
                                                      version="2c",
                                                      community=snmp_community)
            if status > 202:
                queue.put((ip, (False,
                                "Failed to update the switch (status=%d)" %
                                status)))
                return

        switch = resp['switch']
        state = switch['state']
        switch_id = switch['id']

        # if the switch is not in under_monitoring,
        # wait for the poll switch task
        while True:
            status, resp = self._client.get_switch(switch_id)
            if status > 400:
                queue.put((ip, (False, "Failed to get switch status")))
                return

            switch = resp['switch']

            state = switch['state']
            if state == 'initialized' or state == 'repolling':
                time.sleep(10)
            else:
                break

        if state == 'under_monitoring':
            # get machines connected to the switch.
            status, response = self._client.get_machines(switch_id=switch_id)
            if status == 200:
                for machine in response['machines']:
                    queue.put((ip, "mac=%s, vlan=%s, port=%s dbid=%d" % (
                        machine['mac'],
                        machine['vlan'],
                        machine['port'],
                        machine['id'])))
            else:
                queue.put((ip, (False,
                                "Failed to get machines %s" %
                                response['status'])))
        else:
            queue.put((ip, (False, "Switch state is %s" % state)))

if __name__ == "__main__":
    usage = "usage: %prog [options] switch_ips"
    parser = OptionParser(usage)

    parser.add_option("-u", "--server-url", dest="server_url",
                      default="http://localhost/",
                      help="The Compass Server URL")

    parser.add_option("-c", "--community", dest="community",
                      default="public",
                      help="Switch SNMP community string")

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("Wrong number of arguments")

    threads = []
    queue = Queue()
    add_switch = AddSwitch(options.server_url)
    for switch in args[0].split(','):
        t = threading.Thread(target=add_switch.add_switch,
                             args=(queue, switch, options.community))

        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    while True:
        try:
            ip, result = queue.get(block=False)
            print ip, " : ", result
        except Empty:
            break
