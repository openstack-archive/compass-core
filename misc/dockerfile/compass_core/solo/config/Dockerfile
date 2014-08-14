#This images is from the noconfig build. MAKE SURE IT IS TAGGED CORRECTLY OR CHANGE TO FIT NEED!!!
FROM compass:noconfig

MAINTAINER Alexander Hirschfeld (Alexander.Hirschfeld@huawei.com)

#Adding everything into the tmp folder, should contain compass.conf and necessary chef .pem files for knife.
ADD . /tmp/

#technically error checking
WORKDIR ~
RUN ls ~/chef-repo || git clone git://github.com/opscode/chef-repo.git


RUN pip install virtualenvwrapper

#Moving knife file around   
RUN cp -r /tmp/.chef/ ~/.chef

#Checking for compass.conf
#RUN cat compass.conf || echo "If this fails you need to the compass.conf file required for this in the directory."
#This line is error checking, I have removed it because I need more than one file.
RUN ls  ~/.chef
#This is where chef config is finalized.
WORKDIR ~
RUN cat ~/.chef/knife.rb
RUN knife client list
#If client list


WORKDIR /var/chef
#using knife for the cookbooks
RUN knife cookbook upload --all --cookbook-path cookbooks

#Using knife for the databags
RUN for databag in `ls  databags`; do \
       	 knife data bag create $databag; \
    	 for bag in `ls databags/${databag} | egrep '\.json'`; do \
    	     knife data bag from file $databag databags/$databag/$bag; \
	 done; \
    done


#Using knife for roles
RUN for role in `ls ./roles | egrep '\.rb'`; do \
    	knife role from file $role; \
    done


WORKDIR /

RUN sed -i 's/compass check/echo compass check/g' /tmp/compass.sh

#This command runs as soon as the container starts.
#Tailing dhcpd because I don't know what else to tail.
#Docker kills itself after the commands finnish, tail never does so it never dies.

RUN sed -i 's:$ipaddr\/cobbler:$COBBLER_IP\/cobbler:g' tmp/compass.sh
RUN sed -n 45,65p tmp/compass.sh

RUN mkdir -p /var/log/compass
RUN echo start >> /var/log/compass/celeryd.log
RUN echo start >> /var/log/compass/compass.log



CMD source compass-core/install/install.conf.template && \
    source tmp/compass.conf && \
    source `which virtualenvwrapper.sh` && \
    workon compass-core && \
    service rabbitmq-server start && \
    tmp/prepare.sh && \
    tmp/compass.sh && \
    service compassd restart && \
    sleep 10 && \
    service compassd status && \
    deactivate && \
    /bin/bash && \
    tail -f /var/log/compass/compass.log /var/log/compass/celeryd.log

#tail -f /var/log/compass/compass.log /var/log/compass/celeryd.log



#for file in "/var/log/compass/celery.log /var/log/compass/compass.log"; do \
#    tail -f $file & \
#done


#RUN cat /tmp/compass.sh

#WARNING
#To build this docker file, the docker file in NOCONFIG must first be run and tagged as "compass:noconfig"
#This file needs      4	     files to run correctly:
#THese files need to be in a .chef folder.

#     compass.conf    	--for custom installations
#     $user.pem		--for chef/knife
#     $validator.pem	--for chef/knife
#     knife.rb		--for chef/knife

#THIS FILEE WILL NOT COMPLETE INSTALLATION IF IT IS MISSING ANYTHING!!!
