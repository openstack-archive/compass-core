#!/usr/bin/env python

import os
import os.path

databags = []
databag_dir = '/var/chef/databags'
for item in os.listdir(databag_dir):
    databags.append(item)

for databag in databags:
    cmd = "knife data bag create %s" % databag
    os.system(cmd)
    databag_items = []
    databagitem_dir = os.path.join(databag_dir, databag)
    for item in os.listdir(databagitem_dir):
        databag_items.append(os.path.join(databagitem_dir, item))

    for databag_item in databag_items:
        cmd = 'knife data bag from file %s %s' % (databag, databag_item)
        os.system(cmd)
