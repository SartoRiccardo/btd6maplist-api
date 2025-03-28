import http

from .ServerException import ServerException


class MissingPermsException(ServerException):
    def __init__(self, perms: str | list[str], format: int | None = None):
        if isinstance(perms, str):
            perms = [perms]

        error_msg = f"You are missing {','.join(perms)}"
        if format is not None:
            error_msg += f" on format {format}"
        else:
            error_msg += " on any format"
        super().__init__({"format": error_msg}, status_code=http.HTTPStatus.BAD_REQUEST)
