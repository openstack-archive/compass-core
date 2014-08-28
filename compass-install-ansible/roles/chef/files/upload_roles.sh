#!/bin/bash

for i in `ls /var/chef/roles`;do knife role from file /var/chef/roles/$i;done
