from .DiscordRequests import DiscordRequests


__discord_api = DiscordRequests


def discord_api():
    return __discord_api


def set_discord_api(api_class):
    global __discord_api
    __discord_api = api_class
