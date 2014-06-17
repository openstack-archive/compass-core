# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common database query."""
from compass.db import exception
from compass.db.models import BASE


def model_query(session, model, *args, **kwargs):
    """model query."""
    if not issubclass(model, BASE):
        raise DatabaseException("model should be sublass of BASE!")

    return session.query(model)


def model_filter(query, model, filters):
    for key, value in filters.items():
        col_attr = getattr(model, key)
        if isinstance(value, list):
            query = query.filter(col_attr.in_(value))
        else:
            query = query.filter(col_attr == value)

    return query
