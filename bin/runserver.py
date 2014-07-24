#!/usr/bin/env python
#
# Copyright 2014 Huawei Technologies Co. Ltd
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

"""main script to start an instance of compass server ."""
import logging

from compass.api import app
from compass.utils import flags
from compass.utils import logsetting


flags.add('server_host',
          help='server host address',
          default='0.0.0.0')
flags.add_bool('debug',
               help='run in debug mode',
               default=True)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    logging.info('run server')
    app.run(host=flags.OPTIONS.server_host, debug=flags.OPTIONS.debug)
