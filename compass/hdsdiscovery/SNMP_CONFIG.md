Install & Config Prerequisite Packages:

1. Net-Snmp:
   a. #apt-get install -y snmpd snmp libsnmp-python
   b. #apt-get install -y snmp-mibs-downloader
      For Centos:
      # yum install net-snmp net-snmp-utils

   c. create vendor's mibs directory(for example):
      - #mkdir -p /root/.snmp/mibs/huawei
      - #vim /etc/snmp/snmp.conf (if not exists, create snmp.conf file)
           * add vendor;s mibs directory:
             mibdirs +/root/.snmp/mibs/huawei
           * comment the line:
             #mibs:
   d. copy vendor's mibs to that directory
   e. #vim /etc/default/snmpd 
        * modify the directive from
          TRAPDRUN=no --> TRAPDRUN=yes
      For Centos:
      # vim /etc/sysconfig/snmpd
        * modify into or add the directive
          TRAPDRUN=yes     

   f. #vim /etc/snmp/snmpd.conf 
        * add the following line, where $ip is the ip address of manager machine: 
          com2sec mynetwork $ip/24 public
   g. #service snmpd restart

   Note: net-snmp-config is used to see default configuration

2. paramiko: 
   #apt-get install python-paramiko  
