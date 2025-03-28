import re
import yaml
from .Config import Config
from .maps import Map, PartialMap, MinimalMap, RetroMap
from .challenges import LCC, ListCompletion, ListCompletionWithMeta
from .users import User, PartialUser, MaplistProfile, MaplistMedals, MinimalUser
from .Role import Role
from .LeaderboardEntry import LeaderboardEntry
from .MapSubmission import MapSubmission
from .AchievementRole import DiscordRole, AchievementRole, RoleUpdateAction
from .Format import Format
from .Permissions import Permissions

entities = [
    RetroMap,
    Config,
    Map,
    PartialMap,
    MinimalUser,
    MinimalMap,
    LCC,
    ListCompletion,
    ListCompletionWithMeta,
    User,
    PartialUser,
    MaplistProfile,
    LeaderboardEntry,
    MaplistMedals,
    MapSubmission,
    Role,
    DiscordRole,
    AchievementRole,
    RoleUpdateAction,
    Format,
]

swagger_definitions_str = """
DiscordID:
  type: string
  description: an user's Discord ID. Is numeric.
  
RequestUserID:
  type: string
  description: The username or Discord ID of the creator

MaplistFormat:
  type: int
  enum: [1, 2, 51, 52, 11]
  description: >
    The format a run was played in.\\n
    * `1` - Maplist ~ current version.\\n
    * `2` - Maplist ~ all versions.\\n
    * `11` - Nostalgia Pack.\\n
    * `51` - Expert List.\\n
    * `52` - Best of the Best.

ExpertDifficulty:
  type: int
  nullable: true
  enum: [0, 1, 2, 3, 4]
  description: >
    The Expert difficulty.\\n
    * `0` - Casual Expert.\\n
    * `1` - Medium Expert.\\n
    * `2` - High Expert.\\n
    * `3` - True Expert.\\n
    * `4` - Extreme Expert.

MapVersionCompatibility:
  type: int
  enum: [0, 1, 2, 3]
  description: >
    A map's compatibility status with a game version.\\n
    * `0` - No gameplay changes.\\n
    * `1` - Only visual changes.\\n
    * `2` - Playable, but not recommended.\\n
    * `3` - Unplayable and/or has gameplay differences.

Btd6Hero:
  type: string
  enum:
    - quincy
    - gwen
    - obyn
    - striker
    - churchill
    - ben
    - ezili
    - pat
    - adora
    - brickell
    - etienne
    - sauda
    - psi
    - geraldo
    - corvus
    - rosalia
"""


def remove_init_indent(docstring: str, init_padding: int) -> str:
    to_remove = min([
        len(match) for match in re.findall(r"^ +", docstring, flags=re.MULTILINE)]
    )
    return re.sub(
        re.compile("^ {" + str(max(0, to_remove-init_padding)) + "}", flags=re.MULTILINE),
        "",
        docstring
    )


for entity in entities:
    if not entity.__doc__:
        continue

    cls_docs = entity.__doc__.split("---")
    swagger_definitions_str += f"{entity.__name__}:\n{remove_init_indent(cls_docs[0], 2)}\n"
    for extra_cls in cls_docs[1:]:
        swagger_definitions_str += f"{remove_init_indent(extra_cls, 0)}\n"

swagger_definitions = yaml.safe_load(swagger_definitions_str)
