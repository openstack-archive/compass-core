FROM centos:centos6

MAINTAINER Alexander Hirschfeld

#required repos
RUN rpm -Uvh http://download.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
RUN sed -i 's/^mirrorlist=https/mirrorlist=http/g' /etc/yum.repos.d/epel.repo

#installation
RUN yum -y update
RUN yum -y install cobbler cobbler-web createrepo mkisofs python-cheetah  python-simplejson python-urlgrabber PyYAML Django cman debmirror pykickstart dhcp git bind p7zip wget sudo tar


WORKDIR /

#RUN setsebool -P httpd_can_network_connect true

#Cloning repos
RUN git clone https://github.com/stackforge/compass-core.git

#why not?
WORKDIR /tmp/

#poweriso NEEDED TO MOUNT ISOS WITHOUT "mount -o loop"
RUN wget -O poweriso-1.3.tar.gz http://www.poweriso.com/poweriso-1.3.tar.gz
RUN tar -xzvf poweriso-1.3.tar.gz -C /usr/local/bin
RUN chmod +x /usr/local/bin/poweriso
RUN rm poweriso-1.3.tar.gz


#Cloning repos
RUN git clone https://github.com/stackforge/compass-adapters.git

#Renaming repos
RUN mv /tmp/compass-adapters /tmp/adapter

#Setting env
ENV COMPASSDIR '/'

    
#needed variales
#DHCP
#subnet
#oprion routers
#ip range
#ipaddr

#Cobbler Settings
#Nextserver
