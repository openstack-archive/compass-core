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

"""callback lib for config filter callbacks."""


def allow_if_not_empty(_key, ref):
    """allow if ref is not empty."""
    if not ref.config:
        return False
    else:
        return True


def deny_if_empty(_key, ref):
    """deny if ref is empty."""
    if not ref.config:
        return True
    else:
        return False
