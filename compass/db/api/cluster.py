import simplejson as json
from compass.db import api
from compass.db.api import database
from compass.db.api import utils
from compass.db.api.utils import wrap_to_dict
from compass.db.exception import *

from compass.db import utils
from compass.db.config_validation import default_validator
# from compass.db.config_validation import extension

from compass.db.models import Cluster

SUPPORTED_FILTERS = ['name', 'adapter', 'owner']

ERROR_MSG = {
    'findNoCluster': 'Cannot find the Cluster, ID is %d',
}


@wrap_to_dict()
def get_cluster(cluster_id):

    with database.session() as session:
        try:
            cluster = _get_cluster(session, cluster_id)
        except RecordNotExists as ex:
            raise RecordNotExists(ex.message)

        info = cluster.to_dict()

    return info


@wrap_to_dict()
def list_clusters(filters=None):
    """List all users, optionally filtered by some fields"""

    filters = filters or {}
    with database.session() as session:
        clusters = _list_clusters(session, filters)
        clusters_info = [cluster.to_dict() for cluster in clusters]

    return clusters_info


@wrap_to_dict()
def get_cluster_config(cluster_id):
    """Get configuration info for a specified cluster"""

    with database.session() as session:
        try:
            config = _get_cluster_config(session, cluster_id)
        except RecordNotExists as ex:
            raise RecordNotExists(ex.message)

    return config


def _get_cluster_config(session, cluster_id):

    with session.begin(subtransactions=True):
        try:
            cluster = _get_cluster(cluster_id)
        except RecordNotExists as ex:
            raise RecordNotExists(ex.message)

        config = cluster.config

    return config


def _get_cluster(session, cluster_id):
    """Get the adapter by ID"""
    with session.begin(subtransactions=True):
        cluster = session.query(Cluster).filter_by(id=cluster_id).first()
        if not cluster:
            err_msg = ERROR_MSG['findNoCluster'] % cluster_id
            raise RecordNotExists(err_msg)
    return cluster


def _list_clusters(session, filters=None):
    """Get all clusters, optionally filtered by some fields"""

    filters = filters or {}

    with session.begin(subtransactions=True):
        query = api.model_query(session, Cluster)
        clusters = api.model_filter(query, Cluster,
                                    filters, SUPPORTED_FILTERS).all()

    return clusters


def update_cluster_config(cluster_id, root_elem, config, patch=True):
    result = None
    if root_elem not in ["os_config", "package_config"]:
        raise InvalidParameter("Invalid parameter %s" % root_elem)

    with database.session() as session:
        try:
            cluster = _get_cluster(session, cluster_id)
        except RecordNotExists as ex:
            raise RecordNotExists(ex.message)

        id_name = None
        id_value = None
        if root_elem == "os_config":
            id_name = "os_id"
            id_value = getattr(cluster, "os_id")
        else:
            id_name = "adapter_id"
            id_value = getattr(cluster, "adapter_id")

        # Validate config format and values
        is_valid, message = default_validator.validate_config(session,
                                                              config, id_name,
                                                              id_value, patch)
        if not is_valid:
            raise InvalidParameter(message)

        # For addtional validation, you can define functions in extension,
        # for example:
        # os_name = get_os(cluster.os_id)['name']
        # if getattr(extension, os_name):
        #    func = getattr(getattr(extension, os_name), 'validate_config')
        #    if not func(session, os_id, config, patch):
        #        return False

        if root_elem == 'os_config':
            os_config = cluster.os_global_config
            os_config = json.loads(json.dumps(os_config))
            utils.merge_dict(os_config, config)
            cluster.os_global_config = os_config
            result = cluster.os_global_config
        else:
            package_config = cluster.package_global_config
            package_config = json.loads(json.dumps(os_config))
            utils.merge_dict(package_config, config)
            cluster.package_global_config = package_config
            result = cluster.package_global_config

    return result
