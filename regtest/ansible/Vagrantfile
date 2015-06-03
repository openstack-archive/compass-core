Vagrant.configure("2") do |config|
  config.vm.define :compass_vm do |compass_vm|
    compass_vm.vm.box = "precise64"
    compass_vm.vm.network :private_network, :ip=>"10.1.0.11", :libvirt__dhcp_enabled=>false
    compass_vm.vm.provider :libvirt do  |domain|
      domain.memory = 2048
      domain.cpus =2 
      domain.nested =true
      domain.graphics_ip="0.0.0.0"
    end
    compass_vm.vm.provision "ansible" do |ansible|
      ansible.playbook="install/allinone_nochef.yml"
    end
  end
  config.vm.define :compass_nodocker do |compass_nodocker|
    compass_nodocker.vm.box = "centos65"
    compass_nodocker.vm.network :private_network, :ip=>"10.1.0.12", :libvirt__dhcp_enabled=>false
    compass_nodocker.vm.provider :libvirt do  |domain|
      domain.memory = 4096
      domain.cpus =4
      domain.nested =true
      domain.graphics_ip="0.0.0.0"
      domain.management_network_address="192.168.200.0/24"
    end
    compass_nodocker.vm.provision "ansible" do |ansible|
      ansible.playbook="install/compass_nodocker.yml"
#      ansible.tags="debug"
    end
  end
  config.vm.define :regtest_vm do |regtest_vm|
    regtest_vm.vm.box = "centos65"
    regtest_vm.vm.network :private_network, :ip=>"10.1.0.253", :libvirt__dhcp_enabled=>false
    regtest_vm.vm.provider :libvirt do |domain|
      domain.memory = 1024
      domain.cpus = 2
      domain.nested = true
      domain.graphics_ip="0.0.0.0"
    end
    regtest_vm.vm.provision "ansible" do |ansible|
      ansible.playbook="install/regtest.yml"
    end
  end
end
