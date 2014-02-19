"""Module to set the hosts configs from cluster config.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging
from copy import deepcopy

from compass.config_management.utils import config_reference
from compass.utils import util


class ConfigMapping(object):
    """Class to merge cluster config ref to host config ref by path list."""

    def __init__(self, path_list, from_upper_keys={},
                 from_lower_keys={}, to_key='.',
                 override=False, override_conditions={},
                 value=None):
        """Constructor

        :param path_list: list of path to merge from cluster ref to host refs
        :type path_list: list of str
        :param from_upper_keys: kwargs from cluster ref for value callback.
        :type from_upper_keys: dict of kwargs name to path in cluster ref
        :param from_lower_keys: kwargs from host refs for value callback.
        :type from_lower_keys: dict of kwargs name to path in host refs.
        :param to_key: the path in host refs to be merged to.
        :type to_key: str
        :param override: if the path in host ref can be overridden.
        :type override: callback or bool
        :param override_conditions: kwargs from host ref for override callback
        :type override_conditions: dict of kwargs name to path in host ref
        :param value: the value to be set in host refs.
        :type value: callback or any type
        """
        self.path_list_ = path_list
        self.from_upper_keys_ = from_upper_keys
        self.from_lower_keys_ = from_lower_keys
        self.to_key_ = to_key
        self.override_ = override
        self.override_conditions_ = override_conditions
        self.value_ = value

    def __repr__(self):
        return (
            '%s[path_list=%s,from_upper_keys=%s,'
            'from_lower_keys=%s,to_key=%s,override=%s,'
            'override_conditions=%s,value=%s]'
        ) % (
            self.__class__.__name__,
            self.path_list_, self.from_upper_keys_,
            self.from_lower_keys_, self.to_key_,
            self.override_, self.override_conditions_,
            self.value_)

    def _is_valid_path_list(self):
        """Check path_list are valid."""
        for i, path in enumerate(self.path_list_):
            if not isinstance(path, str):
                raise TypeError(
                    'path_list[%d] type is %s while '
                    'expected type is str: %s' % (
                        i, type(path), path))

    def _is_valid_from_upper_keys(self):
        """Check from_upper_keys are valid."""
        for mapping_key, from_upper_key in self.from_upper_keys_.items():
            if not isinstance(from_upper_key, str):
                raise TypeError(
                    'from_upper_keys[%s] type is %s'
                    'while expected type is str: %s' % (
                        mapping_key, type(from_upper_key), from_upper_key))

            if '*' in from_upper_key:
                raise KeyError(
                    'from_upper_keys[%s] %s contains *' % (
                        mapping_key, from_upper_key))

    def _is_valid_from_lower_keys(self):
        """Check from_lower_keys are valid."""
        for mapping_key, from_lower_key in self.from_lower_keys_.items():
            if not isinstance(from_lower_key, str):
                raise TypeError(
                    'from_lower_keys[%s] type'
                    'is %s while expected type is str: %s' % (
                        mapping_key, type(from_lower_key), from_lower_key))

            if '*' in from_lower_key:
                raise KeyError(
                    'from_lower_keys[%s] %s contains *' % (
                        mapping_key, from_lower_key))

    def _is_valid_from_keys(self):
        """Check from keys are valid."""
        self._is_valid_from_upper_keys()
        self._is_valid_from_lower_keys()
        upper_keys = set(self.from_upper_keys_.keys())
        lower_keys = set(self.from_lower_keys_.keys())
        intersection = upper_keys.intersection(lower_keys)
        if intersection:
            raise KeyError(
                'there is intersection between from_upper_keys %s'
                ' and from_lower_keys %s: %s' % (
                    upper_keys, lower_keys, intersection))

    def _is_valid_to_key(self):
        """Check to_key is valid."""
        if '*' in self.to_key_:
            raise KeyError('to_key %s contains *' % self.to_key_)

    def _is_valid_override_conditions(self):
        """Check override conditions are valid."""
        override_items = self.override_conditions_.items()
        for mapping_key, override_condition in override_items:
            if not util.is_instance(override_condition, [str, unicode]):
                raise TypeError(
                    'override_conditions[%s] type is %s '
                    'while expected type is [str, unicode]: %s' % (
                        mapping_key, type(override_condition),
                        override_condition))

            if '*' in override_condition:
                raise KeyError(
                    'override_conditions[%s] %s contains *' % (
                        mapping_key, override_condition))

    def _is_valid(self):
        """Check ConfigMapping instance is valid."""
        self._is_valid_path_list()
        self._is_valid_from_keys()
        self._is_valid_to_key()
        self._is_valid_override_conditions()

    def _get_upper_sub_refs(self, upper_ref):
        """get sub_refs from upper_ref."""
        upper_refs = []
        for path in self.path_list_:
            upper_refs.extend(upper_ref.ref_items(path))

        return upper_refs

    def _get_mapping_from_upper_keys(self, ref_key, sub_ref):
        """Get upper config mapping from from_upper_keys."""
        sub_configs = {}
        for mapping_key, from_upper_key in self.from_upper_keys_.items():
            if from_upper_key in sub_ref:
                sub_configs[mapping_key] = sub_ref[from_upper_key]
            else:
                logging.info('%s ignore from_upper_key %s in %s',
                             self, from_upper_key, ref_key)
        return sub_configs

    def _get_mapping_from_lower_keys(self, ref_key, lower_sub_refs):
        """Get lower config mapping from from_lower_keys."""
        sub_configs = {}
        for mapping_key, from_lower_key in self.from_lower_keys_.items():
            sub_configs[mapping_key] = {}

        for lower_key, lower_sub_ref in lower_sub_refs.items():
            for mapping_key, from_lower_key in self.from_lower_keys_.items():
                if from_lower_key in lower_sub_ref:
                    sub_configs[mapping_key][lower_key] = (
                        lower_sub_ref[from_lower_key])
                else:
                    logging.error(
                        '%s ignore from_lower_key %s in %s lower_key %s',
                        self, from_lower_key, ref_key, lower_key)

        return sub_configs

    def _get_values(self, ref_key, sub_ref, lower_sub_refs, sub_configs):
        """Get values to set to lower configs."""
        if self.value_ is None:
            lower_values = {}
            for lower_key in lower_sub_refs.keys():
                lower_values[lower_key] = deepcopy(sub_ref.config)

            return lower_values

        if not callable(self.value_):
            lower_values = {}
            for lower_key in lower_sub_refs.keys():
                lower_values[lower_key] = deepcopy(self.value_)

            return lower_values

        return self.value_(sub_ref, ref_key, lower_sub_refs,
                           self.to_key_, **sub_configs)

    def _get_override(self, ref_key, sub_ref):
        """Get override from ref_key, ref from ref_key."""
        if not callable(self.override_):
            return bool(self.override_)

        override_condition_configs = {}
        override_items = self.override_conditions_.items()
        for mapping_key, override_condition in override_items:
            if override_condition in sub_ref:
                override_condition_configs[mapping_key] = \
                    sub_ref[override_condition]
            else:
                logging.info('%s no override condition %s in %s',
                             self, override_condition, ref_key)

        return self.override_(sub_ref, ref_key,
                              **override_condition_configs)

    def merge(self, upper_ref, lower_refs):
        """merge upper config to lower configs."""
        upper_sub_refs = self._get_upper_sub_refs(upper_ref)

        for ref_key, sub_ref in upper_sub_refs:
            sub_configs = self._get_mapping_from_upper_keys(ref_key, sub_ref)

            lower_sub_refs = {}
            for lower_key, lower_ref in lower_refs.items():
                lower_sub_refs[lower_key] = lower_ref.setdefault(ref_key)

            lower_sub_configs = self._get_mapping_from_lower_keys(
                ref_key, lower_sub_refs)

            util.merge_dict(sub_configs, lower_sub_configs)

            values = self._get_values(
                ref_key, sub_ref, lower_sub_refs, sub_configs)

            logging.debug('%s set values %s to %s',
                          ref_key, self.to_key_, values)
            for lower_key, lower_sub_ref in lower_sub_refs.items():
                if lower_key not in values:
                    logging.error('no key %s in %s', lower_key, values)
                    continue

                value = values[lower_key]
                lower_to_ref = lower_sub_ref.setdefault(self.to_key_)
                override = self._get_override(self.to_key_, lower_to_ref)
                lower_to_ref.update(value, override)


class ConfigMerger(object):
    """Class to merge clsuter config to host configs."""

    def __init__(self, mappings):
        """Constructor

        :param mappings: list of :class:`ConfigMapping` instance
        """
        self.mappings_ = mappings
        self._is_valid()

    def __repr__(self):
        return '%s[mappings=%s]' % (self.__class__.__name__, self.mappings_)

    def _is_valid(self):
        """Check ConfigMerger instance is valid."""
        if not isinstance(self.mappings_, list):
            raise TypeError(
                '%s mapping type is %s while expect type is list: %s' % (
                    self.__class__.__name__, type(self.mappings_),
                    self.mappings_))

    def merge(self, upper_config, lower_configs):
        """Merge cluster config to host configs.

        :param upper_config: cluster configuration to merge from.
        :type upper_config: dict
        :param lower_configs: host configurations to merge to.
        :type lower_configs: dict of host id to host config as dict
        """
        upper_ref = config_reference.ConfigReference(upper_config)
        lower_refs = {}
        for lower_key, lower_config in lower_configs.items():
            lower_refs[lower_key] = config_reference.ConfigReference(
                lower_config)

        for mapping in self.mappings_:
            logging.debug('apply merging from the rule %s', mapping)
            mapping.merge(upper_ref, lower_refs)

        for lower_key, lower_config in lower_configs.items():
            lower_configs[lower_key] = config_reference.get_clean_config(
                lower_config)

        logging.debug('merged upper config\n%s\nto lower configs:\n%s',
                      upper_config, lower_configs)
