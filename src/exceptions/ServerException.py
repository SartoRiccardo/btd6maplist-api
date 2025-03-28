import http
from aiohttp import web


class ServerException(Exception):
    def __init__(
            self,
            errors: dict[str, str] = None,
            status_code: int = http.HTTPStatus.INTERNAL_SERVER_ERROR
    ):
        self.errors = errors
        self.status_code = status_code

    def to_response(self) -> web.Response:
        if self.errors:
            return web.json_response(
                {"errors": self.errors, "data": {}},
                status=self.status_code
            )
        return web.Response(status=self.status_code)
