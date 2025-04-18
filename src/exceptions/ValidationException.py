import http
from .ServerException import ServerException


class ValidationException(ServerException):
    def __init__(self, errors: dict[str, str]):
        super().__init__(errors=errors, status_code=http.HTTPStatus.BAD_REQUEST)
