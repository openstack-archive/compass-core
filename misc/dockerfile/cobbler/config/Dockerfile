FROM cobbler:noconfig
MAINTAINER Alexander Hirschfeld (Alexander.Hirschfeld@huawei.com)


#Adding in the files that are usefull
#other.sh is the download function in prepare.sh from cobbler-core/install
#It is possible to trim that section out and pipe that to a file, this was faster initially.
#cobbler.conf is sourced after install.conf.template to allow overwriting of variables to customize the install.
ADD other.sh /tmp/other.sh
ADD cobbler.conf /tmp/cobbler.conf
#RUN find / | grep cobbler\.conf
#RUN cat /tmp/cobbler.conf

RUN yum -y update
#RUN yum install -y wget p7zip

WORKDIR /tmp/

#a backup that will become the one run.
RUN cp /compass-core/install/cobbler.sh /tmp/

#THere is probably a better way to do this but this took less thought.
RUN chmod 766 cobbler.sh
RUN chmod 766 other.sh

#just to confirm they are there.
#RUN ls && pwd

#Allowing the appending of cobbler to other
RUN sed -i ':\#!/bin/bash:d' cobbler.sh
#Remove installation
RUN sed -i '/sudo yum/d' cobbler.sh
#remove startup
RUN sed -i '/chkconfig/d' cobbler.sh
#remove SElinux
RUN sed -i '/selinux/d' cobbler.sh
#Remove iptables and make sure nothing crashed because of it...
RUN sed -i 's/echo \"iptables/echo/g' cobbler.sh
RUN sed -i '/iptables/d' cobbler.sh

#replacing ftp with http
RUN sed -i 's|ftp://rpmfind|http://rpmfind|g' cobbler.sh

#I am not sure why I needed to do this, but there seemed to be a bug in the code. It will not do anything if the bug is fixed.
RUN sed -i 's|epel-{CENTOS_IMAGE_VERSION_MAJOR}|epel-${CENTOS_IMAGE_VERSION_MAJOR}|g' cobbler.sh

#Debugging Can be removed, I just have not.
RUN sed -i 's:$ADAPTERS_HOME/cobbler/conf/dhcp.template /etc/cobbler/dhcp.template:$ADAPTERS_HOME/cobbler/conf/dhcp.template /etc/cobbler/dhcp.template; echo $?:g' cobbler.sh

#replacing mount -o loop with something that works
#poweriso extract path_to_iso / -od path_to_outputDirectory
RUN sed -i 's|mount -o loop /var/lib/cobbler/iso/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}.iso /mnt/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}|poweriso extract /var/lib/cobbler/iso/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}.iso / -od /mnt/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}|g' cobbler.sh

RUN sed -i 's|mount -o loop /var/lib/cobbler/iso/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}.iso /mnt/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}|poweriso extract /var/lib/cobbler/iso/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}.iso / -od /mnt/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}|g' cobbler.sh

#removing sudo, Sudo is installed but this was needed. Feel free to debug, it is not needed as docker runs everything as root in containers.
RUN sed -i 's/sudo/ /g' cobbler.sh

#uncomment this line if SElinux is active. I think it works, Not really sure.
#RUN setsebool -P httpd_can_network_connect true


#Making sure install.conf.template is configured correctly. (it is necessary)
RUN sed -i 's/export NIC=installation/export NIC=eth0/g' /compass-core/install/install.conf.template

#Appending cobbler.sh to other.sh
#This gives the code the download function it needed. It is faster than writing another or modifying the script.
#The download function is from the prepare.sh in install or something.
#The cat other.sh commands are not needed outside of debugging.
RUN echo " " >> other.sh
#RUN cat other.sh

RUN cat cobbler.sh >> other.sh

RUN sed -i 's/sudo/ /g' other.sh

#RUN cat other.sh
#RUN mv other.sh temp.sh
#RUN sed -n 1,393p temp.sh >> other.sh
#RUN sed -n 407,421p temp.sh >> other.sh
#RUN sed -n 

#RUN chmod +x other.sh

WORKDIR /
#THE COMMAND
#This is the command that runs everything.
#RUN source /compass-core/install/install.conf.template && \
#    source /tmp/cobbler.conf && \
#    service httpd start && \
#    tmp/other.sh

RUN ls

#Ports that cobbler wants to use
#tftp dhcp
EXPOSE 67
EXPOSE 69
#httpd
EXPOSE 80
#cobbler
EXPOSE 25150
EXPOSE 25151

EXPOSE 22


#RUN source /compass-core/install/install.conf.template && \
#    source /tmp/cobbler.conf && \
#    service httpd start && \
#    tmp/other.sh


#RUN sed -n 1,53p tmp/other.sh >> tmp/tempother.sh
#RUN sed -n 173,216p tmp/other.sh >> tmp/tempother.sh
#RUN sed -n 516,534p tmp/other.sh >> tmp/tempother.sh

#RUN rm tmp/other.sh
#RUN mv tmp/tempother.sh tmp/other.sh

#RUN chmod +x tmp/other.sh




#A mess of commands to get the thing to run on start. maybe?
CMD source /compass-core/install/install.conf.template && \
    source /tmp/cobbler.conf && \
    service httpd start && \
    tmp/other.sh && \
    /bin/bash && \
    tail -f /var/log/cobbler/cobbler.log



#Needed for dhcp from adapters
# $next_server
# $iface.name
# $mac
# $iface.ip_address
# $iface.hostname
# $iface.netmask
# $iface.gateway
# http://$cobbler_server/cblr/svc/op/gpxe/system/$iface.owner
# http://$cobbler_server/cblr/svc/op/gpxe/system/$iface.owner
# $iface.filename

#needed for named conf
# ${zone}
# $zone

