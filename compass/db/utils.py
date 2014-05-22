import copy


def merge_dict(lhs, rhs, override=True):
    """Merge nested right dict into left nested dict recursively.

    :param lhs: dict to be merged into.
    :type lhs: dict
    :param rhs: dict to merge from.
    :type rhs: dict
    :param override: the value in rhs overide the value in left if True.
    :type override: str

    :raises: TypeError if lhs or rhs is not a dict.
    """
    if not rhs:
        return

    if not isinstance(lhs, dict):
        raise TypeError('lhs type is %s while expected is dict' % type(lhs),
                        lhs)

    if not isinstance(rhs, dict):
        raise TypeError('rhs type is %s while expected is dict' % type(rhs),
                        rhs)

    for key, value in rhs.items():
        if (
            isinstance(value, dict) and key in lhs and
            isinstance(lhs[key], dict)
        ):
            merge_dict(lhs[key], value, override)
        else:
            if override or key not in lhs:
                lhs[key] = copy.deepcopy(value)
