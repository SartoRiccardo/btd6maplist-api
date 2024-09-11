import re
import yaml
from .ConfigVar import ConfigVar
from .maps import Map, PartialMap, PartialExpertMap, PartialListMap
from .challenges import LCC, ListCompletion, ListCompletionWithMeta
from .User import User, PartialUser, MaplistProfile
from .LeaderboardEntry import LeaderboardEntry


swagger_definitions_str = """
DiscordID:
  type: string
  description: an user's Discord ID. Is numeric.

MaplistFormat:
  type: int
  enum: [1, 2, 51]
  description: >
    The format a run was played in. Formats 1-50 are for the Maplist, 51-100 are for Expert List.\\n
    * `1` - Maplist ~ current version.\\n
    * `2` - Maplist ~ all versions.\\n
    * `51` - Expert List.

ExpertDifficulty:
  type: int
  enum: [-1, 0, 1, 2, 3]
  description: >
    The Expert difficulty. If none, it's set to `-1`.\\n
    * `0` - Casual Expert.\\n
    * `1` - Medium Expert.\\n
    * `2` - Hard Expert.\\n
    * `3` - True Expert.

MapVersionCompatibility:
  type: int
  enum: [0, 1, 2, 3]
  description: >
    A map's compatibility status with a game version.\\n
    * `0` - No gameplay changes.\\n
    * `1` - Only visual changes.\\n
    * `2` - Playable, but not recommended.\\n
    * `3` - Unplayable and/or has gameplay differences.
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


entities = [
    ConfigVar,
    Map,
    PartialMap,
    PartialExpertMap,
    PartialListMap,
    LCC,
    ListCompletion,
    ListCompletionWithMeta,
    User,
    PartialUser,
    MaplistProfile,
    LeaderboardEntry
]
for entity in entities:
    if not entity.__doc__:
        continue

    cls_docs = entity.__doc__.split("---")
    swagger_definitions_str += f"{entity.__name__}:\n{remove_init_indent(cls_docs[0], 2)}\n"
    for extra_cls in cls_docs[1:]:
        swagger_definitions_str += f"{remove_init_indent(extra_cls, 0)}\n"

swagger_definitions = yaml.safe_load(swagger_definitions_str)
