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

"""Module to setup celery client.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>

   .. note::
      If CELERY_CONFIG_MODULE is set in environment, load celery config from
      the filename declared in CELERY_CONFIG_MODULE.
"""
import os

from celery import Celery


celery = Celery(__name__)
if 'CELERY_CONFIG_MODULE' in os.environ:
    celery.config_from_envvar('CELERY_CONFIG_MODULE')
else:
    from compass.utils import celeryconfig_wrapper as celeryconfig
    celery.config_from_object(celeryconfig)
