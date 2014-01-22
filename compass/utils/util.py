"""Module to provider util functions in all compass code

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
from copy import deepcopy


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
        if (isinstance(value, dict) and key in lhs and
            isinstance(lhs[key], dict)):
            merge_dict(lhs[key], value, override)
        else:
            if override or key not in lhs:
                lhs[key] = deepcopy(value)


def order_keys(keys, orders):
    """Get ordered keys.

    :param keys: keys to be sorted.
    :type keys: list of str
    :param orders: the order of the keys. '.' is all other keys not in order.
    :type orders: list of str.

    :returns: keys as list sorted by orders.

    :raises: TypeError if keys or orders is not list.
    """

    if not isinstance(keys, list):
        raise TypeError('keys %s type should be list' % keys)

    if not isinstance(orders, list):
        raise TypeError('orders ^s type should be list' % orders)

    found_dot = False
    pres = []
    posts = []
    for order in orders:
        if order == '.':
            found_dot = True
        else:
            if found_dot:
                posts.append(order)
            else:
                pres.append(order)

    return ([pre for pre in pres if pre in keys] +
            [key for key in keys if key not in orders] +
            [post for post in posts if post in keys])


def is_instance(instance, expected_types):
    """Check instance type is in one of expected types.

    :param instance: instance to check the type.
    :param expected_types: types to check if instance type is in them.
    :type expected_types: list of type

    :returns: True if instance type is in expect_types.
    """
    for expected_type in expected_types:
        if isinstance(instance, expected_type):
            return True

    return False


def flat_lists_with_possibility(lists):
    """Return list of item from list of list of identity item.

    :param lists: list of list of identity item.

    :returns: list.

    .. note::
       For each first k elements in the returned list, it should be the k
       most possible items. e.g. the input lists is
       ['a', 'a', 'a', 'a'], ['b', 'b'], ['c'],
       the expected output is ['a', 'b', 'c', 'a', 'a', 'b', 'a'].
    """
    lists = deepcopy(lists)
    lists = sorted(lists, key=len, reverse=True)
    list_possibility = []
    max_index = 0
    total_elements = 0
    possibilities = []
    for items in lists:
        list_possibility.append(0.0)
        length = len(items)
        if length > 0:
            total_elements += length
            possibilities.append(1.0/length)
        else:
            possibilities.append(0.0)

    output = []
    while total_elements > 0:
        if not lists[max_index]:
            list_possibility[max_index] -= total_elements
        else:
            list_possibility[max_index] -= possibilities[max_index]
            element = lists[max_index].pop(0)
            output.append(element)
            total_elements -= 1
        max_index = list_possibility.index(max(list_possibility))

    return output


def pretty_print(*contents):
    if len(contents) == 0:
        print ""
    else:
        print "\n".join(content for content in contents)
