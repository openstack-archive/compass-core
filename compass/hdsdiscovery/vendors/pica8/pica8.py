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

"""Vendor: Pica8."""
from compass.hdsdiscovery import base


# Vendor_loader will load vendor instance by CLASS_NAME
CLASS_NAME = 'Pica8'


class Pica8(base.BaseSnmpVendor):
    """Pica8 switch object."""

    def __init__(self):
        base.BaseSnmpVendor.__init__(self, ['pica8'])
        self._name = 'pica8'

    @property
    def name(self):
        """Get 'name' proptery."""
        return self._name
