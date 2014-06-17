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

"""ClusterHost database operations."""
from compass.db import exception
from compass.db import models
from compass.db.api import database
from compass.db.api import utils
from compass.db.api import cluster as cluster_api
from compass.db.api import metadata_holder as metadata_api
from compass.db.api import user as user_api


RESP_FIELDS = [
    'id', 'host_id', 'machine_id', 'name', 'cluster_id',
    'mac', 'os_installed', 'distributed_system_installed',
    'os_name', 'distributed_system_name',
    'owner', 'networks', 'cluster_id'
]
RESP_CONFIG_FIELDS = [
    'package_config'
]
UPDATED_CONFIG_FIELDS = [
    'put_package_config'
]
PATCHED_CONFIG_FIELDS = [
    'patched_package_config'
]
RESP_STATE_FIELDS = [
    'id', 'state', 'progress', 'message', 'severity'
]
UPDATED_STATE_FIELDS = [
    'state', 'progress', 'message', 'severity'
]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def get_clusterhost(getter, clusterhost_id, **kwargs):
    """Get clusterhost info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_CLUSTERHOSTS)
        return utils.get_db_object(
            session, models.Cluster, id=cluster_id
        ).to_dict()


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters([])
def get_clusterhost_config(getter, clusterhost_id, **kwargs):
    """Get clusterhost config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_CLUSTERHOST_CONFIG)
        return utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        ).to_dict()


def _update_clusterhost_config(updater, clusterhost_id, **kwargs):
    """Update a clusterhost config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_CLUSTERHOST_CONFIG)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        )
        check_cluster_editable(session, clusterhost.cluster, updater)
        utils.update_db_object(session, clusterhost, config_validated=False, **kwargs)
        package_config = cluster.package_config
        if package_config:
            metadata_api.validate_package_config(
                package_config, clusterhost.cluster.adapter_id
            )
        return clusterhost.to_dict()


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters(UPDATED_CONFIG_FIELDS)
def update_clusterhost_config(updater, clusterhost_id, **kwargs):
    return _update_clusterhost_config(updater, clusterhost_id, **kwargs)


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters(PATCHED_CONFIG_FIELDS)
def patch_clusterhost_config(updater, clusterhost_id, **kwargs):
    return _update_clusterhost_config(updater, clusterhost_id, **kwargs)


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters([])
def delete_clusterhost_config(deleter, clusterhost_id):
    """Delet a clusterhost config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_DEL_CLUSTERHOST_CONFIG)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        )
        check_cluster_editable(session, clusterhost.cluster, updater)
        utils.update_db_object(
            session, cluster, package_config={}, config_validated=False
        )
        return clusterhost.to_dict()


@utils.wrap_to_dict(RESP_STATE_FIELDS)
@utils.supported_filters([])
def get_clusterhost_state(getter, clusterhost_id, **kwargs):
    """Get clusterhost state info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_GET_CLUSTERHOST_STATE)
        return utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        ).state_dict()


@utils.wrap_to_dict(RESP_STATE_FIELDS)
@utils.supported_filters(UPDATED_STATE_FIELDS)
def update_clusterhost_state(updater, clusterhost_id, **kwargs):
     """Update a clsuterhost state."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_UPDATE_CLUSTERHOST_STATE)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        )
        utils.update_db_object(session, clusterhost.state, **kwargs)
        return clusterhost.state_dict()
