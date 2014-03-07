#!/usr/bin/env python
#
# Copyright 2014 Openstack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""import cookbooks to chef server."""
import logging
import os
import os.path


from compass.utils import flags
from compass.utils import logsetting


flags.add('cookbooks_dir',
          help='chef cookbooks directory',
          default='/var/chef/cookbooks')


def main():
    """main entry."""
    flags.init()
    logsetting.init()
    cookbooks_dir = flags.OPTIONS.cookbooks_dir
    logging.info('add cookbooks %s', cookbooks_dir)
    cmd = "knife cookbook upload --all --cookbook-path %s" % cookbooks_dir
    status = os.system(cmd)
    return status


if __name__ == '__main__':
    main()
