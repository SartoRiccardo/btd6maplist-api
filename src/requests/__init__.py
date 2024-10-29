from .DiscordRequestsMock import DiscordRequestsMock
from .NinjaKiwiMock import NinjaKiwiMock


__discord_api = DiscordRequestsMock
__ninja_kiwi_api = NinjaKiwiMock


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
