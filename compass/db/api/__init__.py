from compass.db.models import BASE


def model_query(session, model, *args, **kwargs):

    if not issubclass(model, BASE):
        raise Exception("model should be sublass of BASE!")

    with session.begin(subtransactions=True):
        query = session.query(model)

    return query


def model_filter(query, model, filters, legal_keys):
    for key in filters:
        if key not in legal_keys:
            continue

        value = filters[key]
        col_attr = getattr(model, key)

        if isinstance(value, list):
            query = query.filter(col_attr.in_(value))
        else:
            query = query.filter(col_attr == value)

    return query
