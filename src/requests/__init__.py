from .DiscordRequests import DiscordRequests
from .NinjaKiwiRequests import NinjaKiwiRequests


__discord_api = DiscordRequests
__ninja_kiwi_api = NinjaKiwiRequests


def discord_api():
    return __discord_api


def set_discord_api(api_class):
    global __discord_api
    __discord_api = api_class


def ninja_kiwi_api():
    return __ninja_kiwi_api


def set_ninja_kiwi_api(api_class):
    global __ninja_kiwi_api
    __ninja_kiwi_api = api_class
