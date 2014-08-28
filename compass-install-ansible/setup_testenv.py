#!/usr/bin/python

from pysphere import VIServer

server = VIServer()
server.connect("10.145.88.64", "root", "1qaz2wsxZX")
vm_names = ['xicheng-ansible-compass', 'xicheng-ansible-cobbler', 'xicheng-ansible-chef']

for vm_name in vm_names:
    vm = server.get_vm_by_name(vm_name)
    print 'Reverting %s to current snapshot...' % vm_name
    vm.revert_to_snapshot()
    print 'Powering on %s...' % vm_name
    vm.power_on()
