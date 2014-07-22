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

"""Permission database operations."""
from compass.db.api import database
from compass.db.api import utils
from compass.db import exception
from compass.db import models


SUPPORTED_FIELDS = ['name', 'alias', 'description']
RESP_FIELDS = ['id', 'name', 'alias', 'description']


class PermissionWrapper(object):
    def __init__(self, name, alias, description):
        self.name = name
        self.alias = alias
        self.description = description

    def to_dict(self):
        return {
            'name': self.name,
            'alias': self.alias,
            'description': self.description
        }


PERMISSION_LIST_PERMISSIONS = PermissionWrapper(
    'list_permissions', 'list permissions', 'list all permissions'
)
PERMISSION_LIST_SWITCHES = PermissionWrapper(
    'list_switches', 'list switches', 'list all switches'
)
PERMISSION_ADD_SWITCH = PermissionWrapper(
    'add_switch', 'add switch', 'add switch'
)
PERMISSION_DEL_SWITCH = PermissionWrapper(
    'delete_switch', 'delete switch', 'delete switch'
)
PERMISSION_LIST_SWITCH_MACHINES = PermissionWrapper(
    'list_switch_machines', 'list switch machines', 'list switch machines'
)
PERMISSION_ADD_SWITCH_MACHINE = PermissionWrapper(
    'add_switch_machine', 'add switch machine', 'add switch machine'
)
PERMISSION_DEL_SWITCH_MACHINE = PermissionWrapper(
    'del_switch_machine', 'delete switch machine', 'del switch machine'
)
PERMISSION_UPDATE_SWITCH_MACHINES = PermissionWrapper(
    'update_switch_machines',
    'update switch machines',
    'update switch machines'
)
PERMISSION_LIST_MACHINES = PermissionWrapper(
    'list_machines', 'list machines', 'list machines'
)
PERMISSION_ADD_MACHINE = PermissionWrapper(
    'add_machine', 'add machine', 'add machine'
)
PERMISSION_DEL_MACHINE = PermissionWrapper(
    'delete_machine', 'delete machine', 'delete machine'
)
PERMISSION_LIST_ADAPTERS = PermissionWrapper(
    'list_adapters', 'list adapters', 'list adapters'
)
PERMISSION_LIST_METADATAS = PermissionWrapper(
    'list_metadatas', 'list metadatas', 'list metadatas'
)
PERMISSION_LIST_NETWORKS = PermissionWrapper(
    'list_networks', 'list networks', 'list networks'
)
PERMISSION_ADD_NETWORK = PermissionWrapper(
    'add_network', 'add network', 'add network'
)
PERMISSION_DEL_NETWORK = PermissionWrapper(
    'del_network', 'del network', 'del network'
)
PERMISSION_LIST_CLUSTERS = PermissionWrapper(
    'list_clusters', 'list clusters', 'list clusters'
)
PERMISSION_ADD_CLUSTER = PermissionWrapper(
    'add_cluster', 'add cluster', 'add cluster'
)
PERMISSION_DEL_CLUSTER = PermissionWrapper(
    'del_cluster', 'del cluster', 'del cluster'
)
PERMISSION_LIST_CLUSTER_CONFIG = PermissionWrapper(
    'list_cluster_config', 'list cluster config', 'list cluster config'
)
PERMISSION_ADD_CLUSTER_CONFIG = PermissionWrapper(
    'add_cluster_config', 'add cluster config', 'add cluster config'
)
PERMISSION_DEL_CLUSTER_CONFIG = PermissionWrapper(
    'del_cluster_config', 'del cluster config', 'del cluster config'
)
PERMISSION_UPDATE_CLUSTER_HOSTS = PermissionWrapper(
    'update_cluster_hosts',
    'update cluster hosts',
    'update cluster hosts'
)
PERMISSION_DEL_CLUSTER_HOST = PermissionWrapper(
    'del_clusterhost', 'delete clusterhost', 'delete clusterhost'
)
PERMISSION_REVIEW_CLUSTER = PermissionWrapper(
    'review_cluster', 'review cluster', 'review cluster'
)
PERMISSION_DEPLOY_CLUSTER = PermissionWrapper(
    'deploy_cluster', 'deploy cluster', 'deploy cluster'
)
PERMISSION_GET_CLUSTER_STATE = PermissionWrapper(
    'get_cluster_state', 'get cluster state', 'get cluster state'
)
PERMISSION_LIST_HOSTS = PermissionWrapper(
    'list_hosts', 'list hosts', 'list hosts'
)
PERMISSION_LIST_HOST_CLUSTERS = PermissionWrapper(
    'list_host_clusters',
    'list host clusters',
    'list host clusters'
)
PERMISSION_UPDATE_HOST = PermissionWrapper(
    'update_host', 'update host', 'update host'
)
PERMISSION_DEL_HOST = PermissionWrapper(
    'del_host', 'del host', 'del host'
)
PERMISSION_LIST_HOST_CONFIG = PermissionWrapper(
    'list_host_config', 'list host config', 'list host config'
)
PERMISSION_ADD_HOST_CONFIG = PermissionWrapper(
    'add_host_config', 'add host config', 'add host config'
)
PERMISSION_DEL_HOST_CONFIG = PermissionWrapper(
    'del_host_config', 'del host config', 'del host config'
)
PERMISSION_LIST_HOST_NETWORKS = PermissionWrapper(
    'list_host_networks',
    'list host networks',
    'list host networks'
)
PERMISSION_ADD_HOST_NETWORK = PermissionWrapper(
    'add_host_network', 'add host network', 'add host network'
)
PERMISSION_DEL_HOST_NETWORK = PermissionWrapper(
    'del_host_network', 'del host network', 'del host network'
)
PERMISSION_GET_HOST_STATE = PermissionWrapper(
    'get_host_state', 'get host state', 'get host state'
)
PERMISSION_UPDATE_HOST_STATE = PermissionWrapper(
    'update_host_state', 'update host sate', 'update host state'
)
PERMISSION_LIST_CLUSTERHOSTS = PermissionWrapper(
    'list_clusterhosts', 'list cluster hosts', 'list cluster hosts'
)
PERMISSION_LIST_CLUSTERHOST_CONFIG = PermissionWrapper(
    'list_clusterhost_config',
    'list clusterhost config',
    'list clusterhost config'
)
PERMISSION_ADD_CLUSTERHOST_CONFIG = PermissionWrapper(
    'add_clusterhost_config',
    'add clusterhost config',
    'add clusterhost config'
)
PERMISSION_DEL_CLUSTERHOST_CONFIG = PermissionWrapper(
    'del_clusterhost_config',
    'del clusterhost config',
    'del clusterhost config'
)
PERMISSION_GET_CLUSTERHOST_STATE = PermissionWrapper(
    'get_clusterhost_state',
    'get clusterhost state',
    'get clusterhost state'
)
PERMISSION_UPDATE_CLUSTERHOST_STATE = PermissionWrapper(
    'update_clusterhost_state',
    'update clusterhost state',
    'update clusterhost state'
)
PERMISSIONS = [
    PERMISSION_LIST_PERMISSIONS,
    PERMISSION_LIST_SWITCHES,
    PERMISSION_ADD_SWITCH,
    PERMISSION_DEL_SWITCH,
    PERMISSION_LIST_SWITCH_MACHINES,
    PERMISSION_ADD_SWITCH_MACHINE,
    PERMISSION_DEL_SWITCH_MACHINE,
    PERMISSION_UPDATE_SWITCH_MACHINES,
    PERMISSION_LIST_MACHINES,
    PERMISSION_ADD_MACHINE,
    PERMISSION_DEL_MACHINE,
    PERMISSION_LIST_ADAPTERS,
    PERMISSION_LIST_METADATAS,
    PERMISSION_LIST_NETWORKS,
    PERMISSION_ADD_NETWORK,
    PERMISSION_DEL_NETWORK,
    PERMISSION_LIST_CLUSTERS,
    PERMISSION_ADD_CLUSTER,
    PERMISSION_DEL_CLUSTER,
    PERMISSION_LIST_CLUSTER_CONFIG,
    PERMISSION_ADD_CLUSTER_CONFIG,
    PERMISSION_DEL_CLUSTER_CONFIG,
    PERMISSION_UPDATE_CLUSTER_HOSTS,
    PERMISSION_DEL_CLUSTER_HOST,
    PERMISSION_REVIEW_CLUSTER,
    PERMISSION_DEPLOY_CLUSTER,
    PERMISSION_GET_CLUSTER_STATE,
    PERMISSION_LIST_HOSTS,
    PERMISSION_LIST_HOST_CLUSTERS,
    PERMISSION_UPDATE_HOST,
    PERMISSION_DEL_HOST,
    PERMISSION_LIST_HOST_CONFIG,
    PERMISSION_ADD_HOST_CONFIG,
    PERMISSION_DEL_HOST_CONFIG,
    PERMISSION_LIST_HOST_NETWORKS,
    PERMISSION_ADD_HOST_NETWORK,
    PERMISSION_DEL_HOST_NETWORK,
    PERMISSION_GET_HOST_STATE,
    PERMISSION_UPDATE_HOST_STATE,
    PERMISSION_LIST_CLUSTERHOSTS,
    PERMISSION_LIST_CLUSTERHOST_CONFIG,
    PERMISSION_ADD_CLUSTERHOST_CONFIG,
    PERMISSION_DEL_CLUSTERHOST_CONFIG,
    PERMISSION_GET_CLUSTERHOST_STATE,
    PERMISSION_UPDATE_CLUSTERHOST_STATE,
]


def list_permissions_internal(session, **filters):
    """internal functions used only by other db.api modules."""
    return utils.list_db_objects(session, models.Permission, **filters)


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
def list_permissions(lister, **filters):
    """list permissions."""
    from compass.db.api import user as user_api
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, PERMISSION_LIST_PERMISSIONS
        )
        return [
            permission.to_dict()
            for permission in utils.list_db_objects(
                session, models.Permission, **filters
            )
        ]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters()
def get_permission(getter, permission_id, **kwargs):
    """get permissions."""
    from compass.db.api import user as user_api
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, PERMISSION_LIST_PERMISSIONS
        )
        permission = utils.get_db_object(
            session, models.Permission, id=permission_id
        )
        return permission.to_dict()


def add_permissions_internal(session):
    """internal functions used by other db.api modules only."""
    permissions = []
    with session.begin(subtransactions=True):
        for permission in PERMISSIONS:
            permissions.append(
                utils.add_db_object(
                    session, models.Permission,
                    True,
                    permission.name,
                    alias=permission.alias,
                    description=permission.description
                )
            )

    return permissions
