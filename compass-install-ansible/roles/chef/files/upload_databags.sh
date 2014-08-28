#!/bin/bash

for i in `ls /var/chef/databags`
do
  knife data bag create $i &&
  for item in `ls /var/chef/databags/$i`
  do
    knife data bag from file $i /var/chef/databags/$i/$item
  done
done
