import http
from .ServerException import ServerException


class GenericErrorException(ServerException):
    def __init__(self, error: str, status_code=http.HTTPStatus.BAD_REQUEST):
        super().__init__({"": error}, status_code=status_code)
