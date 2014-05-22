from flask.ext.restful import Api


class CompassApi(Api):
    # Override the Flask_Restful error routing for 500.
    def error_router(self, original_handler, e):
        code = getattr(e, 'code', 500)
        # for HTTP 500 errors return my custom response
        if code >= 500:
            return original_handler(e)

        return super(Api, self).error_router(original_handler, e)
