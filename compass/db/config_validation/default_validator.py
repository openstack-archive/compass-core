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

"""Default config validation function."""

from sqlalchemy import or_

from compass.db.models import OSConfigField
from compass.db.models import OSConfigMetadata
from compass.db import validator

MAPPER = {
    "os_id": {
        "metaTable": OSConfigMetadata,
        "metaFieldTable": OSConfigField
    }
    # "adapter_id": {
    #     "metaTable": AdapterConfigMetadata,
    #     "metaFieldTable": AdapterConfigField
    # }
}


def validate_config(session, config, id_name, id_value, patch=True):
    """Validates config.

    Validates the given config value according to the config
    metadata of the asscoiated os_id or adapter_id. Returns
    a tuple (status, message).
    """
    if id_name not in MAPPER.keys():
        return (False, "Invalid id type %s" % id_name)

    meta_table = MAPPER[id_name]['metaTable']
    metafield_table = MAPPER[id_name]['metaFieldTable']
    with session.begin(subtransactions=True):
        name_col = name_col = getattr(meta_table, 'name')
        id_col = getattr(meta_table, id_name)

        return _validate_config_helper(session, config,
                                       name_col, id_col, id_value,
                                       meta_table, metafield_table,
                                       patch)


def _validate_config_helper(session, config,
                            name_col, id_col, id_value,
                            meta_table, metafield_table, patch=True):

    with session.begin(subtransactions=True):
        for elem in config:

            obj = session.query(meta_table).filter(name_col == elem)\
                         .filter(or_(id_col is None,
                                     id_col == id_value)).first()

            if not obj and "_type" not in config[elem]:
                return (False, "Invalid metadata '%s'!" % elem)

            if "_type" in config[elem]:
                # Metadata is a variable
                metadata_name = config[elem]['_type']
                obj = session.query(meta_table).filter_by(name=metadata_name)\
                                               .first()

                if not obj:
                    err_msg = ("Invalid metatdata '%s' or missing '_type'"
                               "to indicate this is a variable metatdata."
                               % elem)
                    return (False, err_msg)

                # TODO(Grace): validate metadata here
                del config[elem]['_type']

            fields = obj.fields

            if not fields:
                is_valid, message = _validate_config_helper(session,
                                                            config[elem],
                                                            name_col, id_col,
                                                            id_value,
                                                            meta_table,
                                                            metafield_table,
                                                            patch)
                if not is_valid:
                    return (False, message)

            else:
                field_config = config[elem]
                for key in field_config:
                    field = session.query(metafield_table)\
                                   .filter_by(field=key).first()
                    if not field:
                        # The field is not in schema
                        return (False, "Invalid field '%s'!" % key)

                    value = field_config[key]
                    if field.is_required and value is None:
                        # The value of this field is required
                        # and cannot be none
                        err = "The value of field '%s' cannot be null!" % key
                        return (False, err)

                    if field.validator:
                        func = getattr(validator, field.validator)
                        if not func or not func(value):
                            err_msg = ("The value of the field '%s' is "
                                       "invalid format or None!" % key)
                            return (False, err_msg)

                # This is a PUT request. We need to check presence of all
                # required fields.
                if not patch:
                    for field in fields:
                        name = field.field
                        if field.is_required and name not in field_config:
                            return (False,
                                    "Missing required field '%s'" % name)

        return (True, None)
