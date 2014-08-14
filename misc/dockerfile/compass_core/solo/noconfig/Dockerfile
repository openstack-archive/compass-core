FROM centos:centos6

MAINTAINER Alexander Hirschfeld (Alexander.Hirschfeld@huawei.com)

#dependencies

#The EPEL repo
RUN rpm -Uvh http://download.fedoraproject.org/pub/epel/6/i386/epel-release-6-8.noarch.rpm

#This is te majority of the necessary dependencies, it is split because of previous debugging, and it makes modifying everything easier.
RUN yum -y update
RUN yum -y install git wget which 
RUN yum install -y rsyslog logrotate ntp iproute openssh-clients python python-devel git wget syslinux amqp mod_wsgi httpd 
RUN yum install -y rsync yum-utils gcc net-snmp-utils net-snmp python-daemon unzip openssl openssl098e ca-certificates 
RUN yum install -y redis mysql mysql-server python-virtualenv  
RUN yum -y --enablerepo centosplus install mysql-devel 

#Needed for rabbit
RUN yum install -y erlang

#THis throws an error but does not fail. May need to be changed.
RUN ntpdate 0.centos.pool.ntp.org && \
    service ntpd start && \
    service ntpd status && \
    exit $?

RUN easy_install --upgrade pip

#This may be not working correctly.
RUN pip install virtualenvwrapper

#Compass-core
RUN git clone https://github.com/stackforge/compass-core.git
ENV COMPASSDIR /compass-core/

RUN rpm -Uvh http://www6.atomicorp.com/channels/atomic/centos/6/x86_64/RPMS/atomic-release-1.0-19.el6.art.noarch.rpm

RUN yum install redis -y

WORKDIR /tmp/

#RabbitMQ, the repo installation and the actual installation
RUN rpm --import http://www.rabbitmq.com/rabbitmq-signing-key-public.asc
RUN yum -y install rabbitmq-server

#Chef installating, not yet configured
WORKDIR /

RUN wget https://opscode-omnibus-packages.s3.amazonaws.com/el/6/x86_64/chef-11.8.0-1.el6.x86_64.rpm
RUN rpm -i chef-11.8.0-1.el6.x86_64.rpm
RUN git clone git://github.com/opscode/chef-repo.git
RUN mkdir -p ~/chef-repo/.chef
RUN echo '.chef' >> ~/chef-repo/.gitignore


WORKDIR /tmp/

#Compass.sh prep
RUN cp $COMPASSDIR/install/compass.sh compass.sh

RUN sed -i '/chkconfig/d' compass.sh
#allowing the use of outside services, just sed the IPs in the compass.conf in the config folder. This file is not run in this image.
#RUN sed -i 's|COBBLER_INSTALLER_URL = 'http:\/\/$ipaddr/cobbler_api'|COBBLER_INSTALLER_URL = 'http:\/\/$COBBLER_IP/cobbler_api'|g' compass.sh
#RUN sed -i 's|CHEF_INSTALLER_URL = 'https:\/\/$ipaddr/'|CHEF_INSTALLER_URL = 'https:\/\/$CHEF_IP/'|g' compass.sh
RUN sed -i 's|https:\\\/\\\/$ipaddr|https:\\\/\\\/$CHEF_IP|g' compass.sh
RUN sed -i 's|$CHEF_IP\/cobbler_api|$COBBLER_IP\/cobbler_api|g' compass.sh

RUN sed -n 45,65p compass.sh

RUN sleep 10

#Slopy way to cut out python scripts for knife. The scripts are addcookbooks adddatabags and addroles
RUN mv compass.sh temp.sh
RUN sed -n 1,60p temp.sh >> compass.sh
RUN sed -n 89,147p temp.sh >> compass.sh

RUN cat compass.sh


#Prepare.sh prep This is run, if the file ever changes, this will need to be reworked and checked.
RUN sed -n 1,131p /compass-core/install/prepare.sh >> prepare.sh
RUN sed -n 150,197p /compass-core/install/prepare.sh >> prepare.sh
RUN echo 'source `which virtualenvwrapper.sh`' >> prepare.sh
RUN sed -n 241,316p /compass-core/install/prepare.sh >> prepare.sh
RUN sed -n 340,343p /compass-core/install/prepare.sh >> prepare.sh
RUN sed -n 351,373p /compass-core/install/prepare.sh >> prepare.sh

#Finalizing the files to run in Docker containers.
RUN sed -i 's/sudo//g' prepare.sh
RUN sed -i 's/sudo//g' compass.sh

#Needed to source insstall.conf.template
RUN sed -i 's/export NIC=installation/export NIC=eth0/g' /compass-core/install/install.conf.template

RUN chmod +x prepare.sh
RUN chmod +x compass.sh


WORKDIR /


#Prepwork, it makes installation faster for the config and predownloading everything.
RUN source compass-core/install/install.conf.template && \
    source `which virtualenvwrapper.sh` && \
    tmp/prepare.sh


RUN cp -r /tmp/adapter/* /var
#Apache
EXPOSE 80 
EXPOSE 445 

#rabbinmp
EXPOSE 5672

#Redis
EXPOSE 6379

#Rsyslog
EXPOSE 514

#ntpd
EXPOSE 123

#epmd
EXPOSE 4369

#python --Also used by Cobbler file
EXPOSE 25151

#mysqld
EXPOSE 3306

#THis command is temporaty, it should not be run and is overwritten in the config image.
CMD source compass-core/install/install.conf.template && \
    source `which virtualenvwrapper.sh` && \
    service rabbitmq-server && \
    tmp/prepare.sh && \
    tmp/compass.sh && \
    tail -f /var/log/compass/manage_db.py

