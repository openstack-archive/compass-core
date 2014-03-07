# Copyright 2014 Openstack Foundation
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

"""config provider read config from file.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import json
import logging

from compass.config_management.providers import config_provider
from compass.utils import setting_wrapper as setting


class FileProvider(config_provider.ConfigProvider):
    """config provider which reads config from file."""
    NAME = 'file'

    def __init__(self):
        self.config_dir_ = setting.CONFIG_DIR
        self.global_config_filename_ = setting.GLOBAL_CONFIG_FILENAME
        self.config_file_format_ = setting.CONFIG_FILE_FORMAT

    def _global_config_filename(self):
        """Get global config file name."""
        return '%s/%s' % (
            self.config_dir_, self.global_config_filename_)

    def _config_format(self):
        """Get config file format."""
        return self.config_file_format_

    @classmethod
    def _config_format_python(cls, config_format):
        """Check if config file is stored as python formatted."""
        if config_format == 'python':
            return True
        return False

    @classmethod
    def _config_format_json(cls, config_format):
        """Check if config file is stored as json formatted."""
        if config_format == 'json':
            return True
        return False

    @classmethod
    def _read_config_from_file(cls, filename, config_format):
        """read config from file."""
        config_globals = {}
        config_locals = {}
        content = ''
        try:
            with open(filename) as file_handler:
                content = file_handler.read()
        except Exception as error:
            logging.error('failed to read file %s', filename)
            logging.exception(error)
            return {}

        if cls._config_format_python(config_format):
            try:
                exec(content, config_globals, config_locals)
            except Exception as error:
                logging.error('failed to exec %s', content)
                logging.exception(error)
                return {}

        elif cls._config_format_json(config_format):
            try:
                config_locals = json.loads(content)
            except Exception as error:
                logging.error('failed to load json data %s', content)
                logging.exception(error)
                return {}

        return config_locals

    def get_global_config(self):
        """read global config from file."""
        return self._read_config_from_file(
            self._global_config_filename(),
            self._config_format())


config_provider.register_provider(FileProvider)
