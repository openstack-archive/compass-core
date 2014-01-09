#!/usr/bin/env python

import os
import os.path

cookbooks = []
cookbook_dir = '/var/chef/cookbooks/'
cmd = "knife cookbook upload --all --cookbook-path %s" % cookbook_dir
os.system(cmd)

