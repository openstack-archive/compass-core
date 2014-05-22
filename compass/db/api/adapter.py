from compass.db import api
from compass.db.api import database
from compass.db.api import utils
from compass.db.api.utils import wrap_to_dict
from compass.db.exception import *
from compass.db.models import Adapter
from compass.db.models import OSConfigMetadata
# from compass.db.models import PackageConfigMetadata


SUPPORTED_FILTERS = ['name']

ERROR_MSG = {
    'findNoAdapter': 'Cannot find the Adapter, ID is %d',
    'findNoOs': 'Cannot find OS, ID is %d'
}


@wrap_to_dict()
def get_adapter(adapter_id, return_roles=False):

    with database.session() as session:
        try:
            adapter = _get_adapter(session, adapter_id)
        except RecordNotExists as ex:
            raise RecordNotExists(ex.message)

        info = adapter.to_dict()

        if return_roles:
            roles = adapter.roles
            info = [role.name for role in roles]

    return info


@wrap_to_dict()
def get_adapter_config_schema(adapter_id, os_id):

    with database.session() as session:
        adapter = _get_adapter(session, adapter_id)

        os_list = []
        if not os_id:
            os_list = [os.id for os in adapter.support_os]
        else:
            os_list = [os_id]

        schema = _get_adapter_config_schema(session, adapter_id, os_list)

    return schema


@wrap_to_dict()
def list_adapters(filters=None):
    """List all users, optionally filtered by some fields"""
    if filters:
        filters = utils.get_legal_filters(ADAPTER, filters)

    with database.session() as session:
        adapters = _list_adapters(session, filters)
        adapters_list = [adapter.to_dict() for adapter in adapters]

    return adapters_list


def _get_adapter(session, adapter_id):
    """Get the adapter by ID"""
    with session.begin(subtransactions=True):
        adapter = api.model_query(session, Adapter).first()
        if not adapter:
            err_msg = ERROR_MSG['findNoAdapter'] % adapter_id
            raise RecordNotExists(err_msg)

    return adapter


def _list_adapters(session, filters=None):
    """Get all adapters, optionally filtered by some fields"""

    filters = filters or {}

    with session.begin(subtransactions=True):
        query = api.model_query(session, Adapter)
        adapters = api.model_filter(query, Adapter,
                                    filters, SUPPORTED_FILTERS).all()

    return adapters


# TODO(Grace): TMP method
def _get_adapter_config_schema(session, adapter_id, os_list):
    output_dict = {}

    with session.begin(subtransactions=True):
        os_root = session.query(OSConfigMetadata).filter_by(name="os_config")\
                                                 .first()
        # pk_root = session.query(PackageConfigMetadata\
        #                  .filter_by(name="os_config").first()

        os_config_list = []
        for os_id in os_list:
            os_config_dict = {"_name": "os_config"}
            output_dict = {}
            output_dict["os_config"] = os_config_dict
            _get_adapter_config_helper(os_root, os_config_dict,
                                       output_dict, "os_id", os_id)
            result = {"os_id": os_id}
            result.update(output_dict)
            os_config_list.append(result)
        """
        package_config_dict = {"_name": "package_config"}
        output_dict = {}
        output_dict["package_config"] = package_config_dict
        _get_adapter_config_internal(pk_root, package_config_dict,
                                     output_dict, "adapter_id", adapter_id)
        """
        output_dict = {}
        output_dict["os_config"] = os_config_list

    return output_dict


# A recursive function
# This assumes that only leaf nodes have field entry and that
# an intermediate node in config_metadata table does not have field entries
def _get_adapter_config_helper(node, current_dict, parent_dict,
                               id_name, id_value):
    children = node.children

    if children:
        for c in children:
            col_value = getattr(c, id_name)
            if col_value is None or col_value == id_value:
                child_dict = {"_name": c.name}
                current_dict[c.name] = child_dict
                _get_adapter_config_helper(c, child_dict, current_dict,
                                           id_name, id_value)
        del current_dict["_name"]
    else:
        fields = node.fields
        fields_dict = {}

        for field in fields:
            info = field.to_dict()
            name = info['field']
            del info['field']
            fields_dict[name] = info

        parent_dict[current_dict["_name"]] = fields_dict
