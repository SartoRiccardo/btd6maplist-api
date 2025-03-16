import random
import string
from dataclasses import dataclass
from typing import Any
from datetime import datetime

# Code for this file is unkept and made kind of hastily

USER_COUNT = 50
MAP_COUNT = 60
MAP_SUBMISSION_COUNT = 120
NULLSTR = "\\N"
SEPARATOR = "\t"
BR = "\n"

start_timestamp = 1728770986
del_timestamp = 1728770986 + 3600*24
images = [
    "https://dummyimage.com/300x200/000/fff",
    "https://dummyimage.com/400x300/00ff00/000",
    "https://dummyimage.com/600x400/0000ff/fff",
    "https://dummyimage.com/800x600/ff0000/fff",
    "https://dummyimage.com/200x200/ff00ff/fff",
    "https://dummyimage.com/500x300/ffff00/000",
    "https://dummyimage.com/700x500/ff6600/fff",
    "https://dummyimage.com/900x700/663399/fff",
    "https://dummyimage.com/250x150/9966cc/fff",
    "https://dummyimage.com/450x350/00cccc/000",
    "https://dummyimage.com/650x450/cc00cc/fff",
    "https://dummyimage.com/850x650/339966/fff",
    "https://dummyimage.com/150x100/ff9933/000",
    "https://dummyimage.com/350x250/33cc99/fff",
    "https://dummyimage.com/550x350/3399ff/000",
    "https://dummyimage.com/750x550/996633/fff",
    "https://dummyimage.com/950x750/cc9966/fff",
    "https://dummyimage.com/100x100/6699cc/000",
    "https://dummyimage.com/300x250/663366/fff",
    "https://dummyimage.com/500x400/ff6699/000",
]
allowed_heros = [
    "quincy", "gwen", "obyn", "striker", "churchill", "ben", "ezili", "pat", "adora", "brickell", "etienne",
    "sauda", "psi", "geraldo", "corvus", "rosalia",
]


def nullify(data: Any | None) -> str:
    if data is None:
        return NULLSTR
    return str(data)


def num_to_letters(num: int):
    letters = ""
    while num > 0:
        letters = chr(num % 10 + ord('A')) + letters
        num = num // 10
    letters = "A"*max(2-len(letters), 0) + letters
    letters = "X"*max(3-len(letters), 0) + letters
    return letters


def dateify(timestamp: int | None) -> str:
    if timestamp is None:
        return NULLSTR
    date = datetime.fromtimestamp(timestamp)
    return date.strftime("%Y-%m-%d %H:%M:%S.000000")


def stringify(*args: Any) -> list[str]:
    return [nullify(x) for x in args]


def rm_nulls(l: list[Any | None]) -> list:
    return [x for x in l if x is not None]


def difficultify(diff: int) -> str:
    return nullify(None if diff == -1 else diff)


def User(user_id: int) -> str:
    name = f"usr{user_id}"
    if user_id == 100000:
        name = "Authenticated User"

    return SEPARATOR.join(stringify(
        user_id,
        name,
        nullify(None),
        True,
    ))


@dataclass
class MapKey:
    code: str


@dataclass
class Map:
    id: int
    code: str
    name: str
    placement_cur: int
    placement_all: int
    difficulty: int
    r6_start: str | None
    deleted_on: int | None
    map_preview_url: str | None
    new_version: int | None
    created_on: int
    optimal_heros: list[str]
    # Many-To-One
    creators: list[tuple[int, str | None]]
    additional_codes: list[tuple[str, str | None]]
    verifications: list[tuple[str, int]]
    map_data_compatibility: list[tuple[int, int]]
    aliases: list[str]
    # New fields
    botb_difficulty: int | None = None
    remake_of: int | None = None

    def dump_map(self) -> str:
        return SEPARATOR.join(stringify(
            self.code,
            self.name,
            nullify(self.r6_start),
            nullify(None),
            nullify(self.map_preview_url),
        ))

    def dump_map_meta(self) -> str:
        return SEPARATOR.join(stringify(
            self.id,
            self.code,
            difficultify(self.placement_cur),
            difficultify(self.placement_all),
            difficultify(self.difficulty),
            ";".join(self.optimal_heros),
            difficultify(self.botb_difficulty),
            difficultify(self.remake_of),
            dateify(self.created_on),
            dateify(self.deleted_on),
            nullify(self.new_version),
        ))

    def dump_aliases(self) -> str:
        return "\n".join(
            SEPARATOR.join(
                stringify(alias, self.code)
            ) for alias in self.aliases
        )

    def dump_add_codes(self) -> str:
        return "\n".join(
            SEPARATOR.join(
                stringify(code, descr, self.code)
            ) for code, descr in self.additional_codes
        )

    def dump_verifications(self) -> str:
        return "\n".join(
            SEPARATOR.join(
                stringify(user_id, nullify(version), self.code)
            ) for user_id, version in self.verifications
        )

    def dump_creators(self) -> str:
        return "\n".join(
            SEPARATOR.join(
                stringify(user_id, nullify(role), self.code)
            ) for user_id, role in self.creators
        )


@dataclass
class MapSubmission:
    code: str
    submitter: int
    subm_notes: str | None
    for_list: int
    proposed: int
    rejected_by: int | None
    created_on: int
    completion_proof: str
    wh_data: str | None

    def dump_submission(self) -> str:
        return SEPARATOR.join(stringify(
            self.code,
            self.submitter,
            self.subm_notes,
            self.for_list,
            self.proposed,
            self.rejected_by,
            dateify(self.created_on),
            self.completion_proof,
            self.wh_data,
        ))


@dataclass
class LCC:
    id: int
    leftover: int

    def dump_lcc(self):
        return SEPARATOR.join(stringify(
            self.id,
            self.leftover,
        ))


@dataclass
class Completion:
    id: int
    map: Map | MapKey
    black_border: bool
    no_geraldo: bool
    created_on: int
    deleted_on: int | None
    new_version: int | None
    accepted_by: int | None
    format: int
    subm_notes: str | None
    subm_wh_payload: str | None
    # One-to-one
    lcc: LCC | None
    # Many-to-one
    players: list[int]
    subm_proof_img: list[str]
    subm_proof_vid: list[str]

    @property
    def comp_meta_id(self):
        return self.id + (-1 if self.id % 2 == 0 else 1)

    def dump_completion(self) -> str:
        return SEPARATOR.join(stringify(
            self.id,
            self.map.code,
            dateify(self.created_on),
            self.subm_notes,
            self.subm_wh_payload,
            None,  # Copied from ID
        ))

    def dump_completion_meta(self) -> str:
        return SEPARATOR.join(stringify(
            self.comp_meta_id,
            self.id,
            self.black_border,
            self.no_geraldo,
            self.lcc.id if self.lcc else None,
            dateify(self.created_on),
            dateify(self.deleted_on),
            self.new_version,
            self.accepted_by,
            self.format,
            None,  # Copied from ID
        ))

    def dump_players(self) -> str:
        return "\n".join(
            SEPARATOR.join(stringify(user_id, self.comp_meta_id))
            for user_id in self.players
        )

    def dump_proofs(self) -> str:
        return "\n".join([
            *[
                SEPARATOR.join(stringify(self.id, url, 0))
                for url in self.subm_proof_img
            ],
            *[
                SEPARATOR.join(stringify(self.id, url, 1))
                for url in self.subm_proof_vid
            ],
        ])


@dataclass
class AchievementRole:
    lb_format: int
    lb_type: str
    threshold: int
    for_first: bool
    tooltip_description: str | None
    name: str
    clr_border: int
    clr_inner: int
    # Many-to-one
    linked_roles: list[tuple[int, int]]

    def dump_ach_roles(self) -> str:
        return SEPARATOR.join(stringify(
            self.lb_format,
            self.lb_type,
            self.threshold,
            self.for_first,
            self.tooltip_description,
            self.name,
            self.clr_border,
            self.clr_inner,
        ))

    def dump_linked_roles(self) -> str:
        return "\n".join([
            SEPARATOR.join(
                stringify(self.lb_format, self.lb_type, self.threshold, guild, role)
            )
            for guild, role in self.linked_roles
        ])


def rand_str(rand: random.Random, k: int = 10) -> str:
    return "".join(rand.choices(string.ascii_letters, k=k))


def random_achivement_roles() -> list[AchievementRole]:
    rand_discord = random.Random(93416)
    rand_clr = random.Random(36157)

    def clr() -> int:
        return rand_clr.randint(0, 0xffffff)

    def disc_roles() -> list[tuple[int, int]]:
        return [
            (rand_discord.randint(1000000000000, 10000000000000), rand_discord.randint(1000000000000, 10000000000000))
            for _ in range(3)
        ][:rand_discord.randint(1, 3)]

    return [
        AchievementRole(1, "points", 0, True, "First", "List Champ", clr(), clr(), disc_roles()),
        AchievementRole(1, "points", 1, False, "1+ points", "List lv1", clr(), clr(), disc_roles()),
        AchievementRole(1, "points", 100, False, "100+ points", "List lv2", clr(), clr(), disc_roles()),
        AchievementRole(1, "points", 300, False, "300+ points", "List lv3", clr(), clr(), disc_roles()),

        AchievementRole(1, "black_border", 0, True, None, "List BBChamp", clr(), clr(), disc_roles()),
        AchievementRole(1, "black_border", 1, False, "1+ BB", "List BBlv1", clr(), clr(), disc_roles()),

        AchievementRole(51, "points", 0, True, "FirstExp", "Experts Champ", clr(), clr(), []),
        AchievementRole(51, "points", 1, False, None, "Experts lv1", clr(), clr(), []),
        AchievementRole(51, "points", 15, False, None, "Experts lv2", clr(), clr(), disc_roles()),
    ]


def random_map_submissions() -> list[MapSubmission]:
    rand_rejector = random.Random(9813)
    rand_images = random.Random(53175)
    submissions = []

    for i in range(MAP_SUBMISSION_COUNT):
        submissions.append(
            MapSubmission(
                f"SUBX{num_to_letters(i)}",
                ((i // 3) % USER_COUNT)+1,
                None if i < 40 else f"Submission notes for map {i}",
                (i // 4) % 2,
                (i // 5) % 7,
                rand_rejector.randint(1, USER_COUNT+1) if (i+7) % 13 == 0 else None,
                start_timestamp + i*3600 * (-1 if i % 23 == 0 else 1),
                rand_images.choice(images),
                None,
            )
        )
    for i in range(10):
        submissions.append(
            MapSubmission(
                f"MLXX{num_to_letters(i)}",
                1,
                None,
                0,
                0,
                2 if i % 2 == 0 else None,
                start_timestamp - i*3600,
                rand_images.choice(images),
                None,
            )
        )

    return submissions


def random_maps() -> tuple[int, list[Map]]:
    rand_creat = random.Random(500)
    rand_map_url = random.Random(500)
    rand_heros = random.Random(500)
    rand_images = random.Random(500)
    map_uid = 1

    maps = []
    for plc in range(1, MAP_COUNT+1):
        creat1 = rand_creat.randint(1, USER_COUNT)
        creat2 = creat1
        while creat2 == creat1:
            creat2 = rand_creat.randint(1, USER_COUNT)

        maps.append(Map(
            map_uid,
            f"MLXX{num_to_letters(plc-1)}",
            f"Maplist Map {plc}",
            plc,
            plc-5 if 1 < plc-5 <= 50 else (50 + (plc-55)//2) if (plc-5) % 2 == 0 and plc-5 > 50 else -1,
            -1 if plc < 40 or plc >= 55 else plc % 4,
            (
                None if plc < 20 else
                f"https://youtu.be/{rand_str(rand_images)}" if plc < 30 else
                rand_images.choice(images) if plc < 40 else
                f"https://drive.google.com/file/d/{rand_str(rand_images, k=32)}/view"
            ),
            None,
            (
                None if plc < 40 else
                rand_map_url.choice(images)
            ),
            None,
            start_timestamp,
            rand_heros.choices(allowed_heros, k=(1 if plc < 40 else 2 if plc < 45 else 0)),

            rm_nulls([
                (creat1, None if plc < 30 else "Gameplay"),
                None if plc < 15 else (creat2, None if plc < 30 else "Decoration"),
            ]),
            rm_nulls([
                None if plc < 25 else (f"MLA1X{plc:0>2}", "Additional Code 1"),
                None if plc < 45 else (f"MLA2X{plc:0>2}", "Additional Code 2"),
            ]),
            rm_nulls([
                None if plc < 10 else (10, None),
                None if plc < 20 else (10, 441),
                None if plc < 30 else (12, 441),
                None if plc < 40 else (10, 440),
                None if plc < 40 else (12, None),
            ]),
            [],  # map_data_compatibility,
            rm_nulls([
                None if plc < 10 else f"ml{plc}",
                None if plc < 20 else f"ml_{plc}",
                None if plc < 40 else f"Maplist Map {plc-5}",
                None if plc < 40 else f"MLXXX{plc-5:0>2}",
                None if plc < 40 else f"{plc-5}",
                None if plc < 40 else f"@{plc-39}",
                None if plc < 45 or plc > 50 else f"deleted_maplist_map_{plc-45}",
            ]),
        ))
        map_uid += 1

    for i in range(1, 11):
        maps.append(Map(
            map_uid,
            f"DELX{num_to_letters(i)}",
            f"Deleted Maplist Map {i}",
            -1,
            -1,
            -1,
            None,
            del_timestamp,
            None,
            None,
            start_timestamp,
            rand_heros.choices(allowed_heros, k=(1 if plc < 40 else 2 if plc < 45 else 0)),
            [],
            [],
            [],
            [],
            [f"deleted_map_alias{i}", f"other_deleted_map_alias{i}"],
        ))
        map_uid += 1

    return map_uid, maps


def gen_video_proofs(rand: random.Random, k: int = 10) -> list[str]:
    return [f"https://youtu.be/{''.join(rand.sample(string.ascii_letters, k=8))}" for _ in range(k)]


def random_completions(maps: list[Map]) -> tuple[int, int, list[Completion]]:
    rand_usr = random.Random(9161459)
    rand_player = random.Random(315718)
    rand_amount = random.Random(31653)
    rand_leftover = random.Random(56671)
    rand_proofs = random.Random(79155)
    rand_youtube = random.Random(981345)

    formats = [1, 2, 51]

    comp_uid = 1
    lcc_uid = 1
    completions = []
    for map in maps:
        comps_to_add = 120 if map.code == "MLXXXAB" else \
            0 if map.id % 32 == 0 else \
            rand_amount.randint(1, 10)

        if comps_to_add == 0:
            continue

        for i in range(comps_to_add):
            seed = map.id + comp_uid

            video_proofs = gen_video_proofs(rand_youtube)
            players = []
            while len(players) < 3:
                if (ply := rand_player.randint(1, USER_COUNT)) not in players:
                    players.append(ply)
            ply_count = 2 if seed % 30 < 15 else 3 if seed % 30 < 23 else 1

            lcc = None
            if i == 0 or seed % 257 == 0 or seed % 22 == 0:
                lcc = LCC(lcc_uid, rand_leftover.randint(10000, 20000))
                lcc_uid += 1

            completions.append(Completion(
                comp_uid,
                map,
                seed % 43 == 0 or seed % 55 == 0 or seed % 257 == 0,
                seed % 27 == 0 or seed % 55 == 0 or seed % 257 == 0,
                start_timestamp + 3600 * (seed % 100),
                None if seed % 33 != 0 else del_timestamp,
                None,
                None if (seed+13) % 25 in [1, 4, 6, 19] else rand_usr.randint(1, USER_COUNT),
                formats[(seed // 6) % 3],
                None if seed % 45 < 31 else f"Submission notes for {comp_uid}",
                None,
                lcc,
                players[:ply_count],
                rand_proofs.choices(images, k=(seed % 20) // 5),
                rand_proofs.choices(video_proofs, k=(seed % 20) % 4),
            ))
            comp_uid += 1

    return comp_uid, lcc_uid, completions


def pro_user_completions(maps: list[Map], comp_uid: int = 1, lcc_uid: int = 1) -> tuple[int, int, list[Completion]]:
    rand_player = random.Random(315718)
    rand_lcc = random.Random(56671)
    rand_proofs = random.Random(79155)
    rand_youtube = random.Random(981345)
    rand_amount = random.Random(51054)
    user_good_at_the_game = 42

    completions = []
    for map in maps:
        if map.code in ["MLXXXAB", "MLXXXAJ"]:
            continue

        for _ in range(rand_amount.randint(1, 3)):
            seed_pro_user = 42 + comp_uid
            video_proofs = gen_video_proofs(rand_youtube)
            lcc = None
            if rand_lcc.random() > 0.8:
                lcc = LCC(lcc_uid, rand_lcc.randint(10000, 20000))
                lcc_uid += 1

            players = [user_good_at_the_game]
            if rand_player.random() < 0.8 and (add_ply := rand_player.randint(1, USER_COUNT)) != 21:
                players.append(add_ply)

            completions.append(Completion(
                comp_uid,
                map,
                seed_pro_user % 43 == 0 or seed_pro_user % 55 == 0 or seed_pro_user % 257 == 0,
                seed_pro_user % 27 == 0 or seed_pro_user % 55 == 0 or seed_pro_user % 257 == 0,
                start_timestamp + 3600 * (seed_pro_user % 100),
                None,
                None,
                3,
                1,
                None if seed_pro_user % 45 < 31 else f"Submission notes for {comp_uid}",
                None,
                lcc,
                players,
                rand_proofs.choices(images, k=(seed_pro_user % 20) // 5),
                rand_proofs.choices(video_proofs, k=(seed_pro_user % 20) % 4),
            ))
            comp_uid += 1

    return comp_uid, lcc_uid, completions


def completions_recent(map: Map, comp_uid: int = 1, lcc_uid: int = 1) -> tuple[int, int, list[Completion]]:
    """Doubles as recent comple"""
    rand_proofs = random.Random(461883)
    rand_players = random.Random(6739)
    video_proofs = gen_video_proofs(random.Random(15674916))

    player_id = 8

    def new_completion(
            max_proof: bool = False,
            max_players: bool = False,
            deleted: bool = False,
            accepted: bool = True,
            run_format: int = 1,
            with_lcc: bool = False,
    ) -> Completion:
        nonlocal lcc_uid, comp_uid
        players = [player_id]
        if max_players:
            players += [rand_players.randint(1, USER_COUNT), rand_players.randint(1, USER_COUNT)]

        lcc = None
        if with_lcc:
            lcc = LCC(lcc_uid, 999999)
            lcc_uid += 1

        comp = Completion(  # Minimal completion
            comp_uid,
            map,
            False,
            False,
            start_timestamp + 3600*24*7,
            (start_timestamp + 3600*24*7 + 10) if deleted else None,
            None,
            3 if accepted else None,
            run_format,
            None,
            None,
            lcc,
            players,
            rand_proofs.choices(images, k=1 if not max_proof else 4),
            rand_proofs.choices(video_proofs, k=1 if not max_proof else 5),
        )
        comp_uid += 1
        return comp

    completions = [
        new_completion(),
        new_completion(accepted=False, with_lcc=True),
        new_completion(accepted=True, with_lcc=True, max_proof=True, max_players=True),
        new_completion(deleted=True),
        new_completion(max_players=True, run_format=2),
    ]

    return comp_uid, lcc_uid, completions


def gen_extra_lccs(map: Map, comp_uid: int = 1, lcc_uid: int = 1) -> tuple[int, int, list[Completion]]:
    def new_completion() -> Completion:
        nonlocal lcc_uid, comp_uid
        comp = Completion(
            comp_uid,
            map,
            False,
            False,
            start_timestamp + 3600,
            None if lcc_uid % 2 == 0 else start_timestamp + 4600,
            None,
            None if lcc_uid % 3 == 0 else 3,
            1,
            None,
            None,
            LCC(lcc_uid, lcc_uid * 1000),
            [19],
            [],
            [],
        )
        comp_uid += 1
        lcc_uid += 1
        return comp

    lccs = [new_completion() for _ in range(12)]
    return comp_uid, lcc_uid, lccs


def gen_extra_maps(map_uid: int = 1) -> tuple[int, list[Map]]:
    maps = [
        Map(
            map_uid, "MLAXXAA", f"Maplist Map All Versions 1",
            -1, 1, -1,
            None, None, None, None,
            start_timestamp,
            ["geraldo"], [(1, None)], [], [], [], [],
        ),
        Map(
            map_uid+1, "ELXXXAA", f"Expert Map 1",
            -1, -1, 1,
            None, None, None, None,
            start_timestamp,
            ["geraldo"], [(1, None)], [], [], [], [],
        ),
    ]
    map_uid += len(maps)
    return map_uid, maps


def gen_lb_completions(map: Map, comp_uid: int = 1, lcc_uid: int = 1) -> tuple[int, int, list[Completion]]:
    rand_comps = random.Random(3157)
    comps = []
    for seed in range(2**3):
        no_geraldo = bool(seed & 0b001)
        black_border = bool(seed & 0b010)
        has_lcc = bool(seed & 0b100)

        for x in range(rand_comps.randint(1, 2)):
            comps.append(
                Completion(
                    comp_uid,
                    map,
                    no_geraldo,
                    black_border,
                    start_timestamp + comp_uid,
                    None,
                    None,
                    3,
                    1,
                    None,
                    None,
                    LCC(lcc_uid, 999_999_999) if has_lcc else None,
                    [47],
                    [],
                    [],
                )
            )
            comp_uid += 1
            if has_lcc:
                lcc_uid += 1

    return comp_uid, lcc_uid, comps


def gen_misc_completions(comp_uid: int = 1, lcc_uid: int = 1) -> tuple[int, int, list[Completion]]:
    comps = [
        Completion(comp_uid, MapKey("MLXXXEJ"), False, True, start_timestamp, None, None, 2, 51, None, None, None, [1], [], [])
    ]
    return comp_uid+len(comps), lcc_uid, comps


def gen_round_completions(comp_uid: int) -> tuple[int, list[Completion]]:
    if comp_uid % 2 == 0:
        return comp_uid+1, [
            Completion(
                comp_uid,
                MapKey("MLXXXEJ"),
                True,
                True,
                start_timestamp + 1,
                None,
                3,
                None if lcc_uid % 3 == 0 else 3,
                1,
                None,
                None,
                LCC(lcc_uid, lcc_uid * 1000),
                [19, 40, 41],
                [],
                [],
            ),
        ]
    return comp_uid, []


if __name__ == '__main__':
    import os
    from pathlib import Path

    bpath = Path(os.path.dirname(os.path.abspath(__file__)))
    map_uid, maps = random_maps()
    map_submissions = random_map_submissions()
    comp_uid, lcc_uid, completions = random_completions(maps)
    comp_uid, lcc_uid, completions_pro = pro_user_completions(maps, comp_uid=comp_uid, lcc_uid=lcc_uid)
    comp_uid, lcc_uid, completions_rec = completions_recent(maps[10], comp_uid=comp_uid, lcc_uid=lcc_uid)
    comp_uid, lcc_uid, completions_lccs = gen_extra_lccs(maps[0], comp_uid=comp_uid, lcc_uid=lcc_uid)
    comp_uid, lcc_uid, completions_lb = gen_lb_completions(maps[37], comp_uid=comp_uid, lcc_uid=lcc_uid)
    comp_uid, lcc_uid, completions_misc = gen_misc_completions(comp_uid=comp_uid, lcc_uid=lcc_uid)
    comp_uid, completions_round = gen_round_completions(comp_uid=comp_uid)
    completions += completions_rec + \
                   completions_pro + \
                   completions_lccs + \
                   completions_lb + \
                   completions_misc + \
                   completions_round

    map_uid, extra_maps = gen_extra_maps(map_uid)
    maps += extra_maps

    achievement_roles = random_achivement_roles()

    with open(bpath / "01_maps.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_map() for x in maps
        ))
    with open(bpath / "12_map_list_meta.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_map_meta() for x in maps
        ))
    with open(bpath / "02_users.csv", "w") as fout:
        fout.write("\n".join(
            User(user_id) for user_id in range(1, USER_COUNT+1))
        )
        fout.write(f"\n{User(100000)}")
    with open(bpath / "03_map_aliases.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_aliases() for x in maps
            if len(x.dump_aliases())
        ))
    with open(bpath / "04_additional_codes.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_add_codes() for x in maps
            if len(x.dump_add_codes())
        ))
    with open(bpath / "05_verifications.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_verifications() for x in maps
            if len(x.dump_verifications())
        ))
    with open(bpath / "06_creators.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_creators() for x in maps
            if len(x.dump_creators())
        ))
    with open(bpath / "07_map_submissions.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_submission() for x in map_submissions
        ))
    with open(bpath / "20_completions.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_completion() for x in completions
        ))
    with open(bpath / "23_comp_players.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_players() for x in completions
        ))
    with open(bpath / "22_completion_proofs.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_proofs() for x in completions
            if len(x.subm_proof_img) + len(x.subm_proof_vid)
        ))
    with open(bpath / "21_completions_meta.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_completion_meta() for x in completions
        ))
    with open(bpath / "08_leastcostchimps.csv", "w") as fout:
        fout.write("\n".join(
            x.lcc.dump_lcc() for x in completions
            if x.lcc is not None
        ))
    with open(bpath / "10_achievement_roles.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_ach_roles() for x in achievement_roles
        ))
    with open(bpath / "11_discord_roles.csv", "w") as fout:
        fout.write("\n".join(
            x.dump_linked_roles() for x in achievement_roles
            if len(x.linked_roles)
        ))

    p21_total = 0
    p21_not_accepted = 0
    p21_deleted_on = 0
    p21_format_2 = 0
    p21_del_map = 0
    runs_format = {"tot": 0, "na": 0, "del": 0, "fmt2": 0, "delmap": 0}
    players_runs = {
        42: {**runs_format},
        21: {**runs_format},
        8: {**runs_format},
    }
    for cmp in completions:
        for pl_id in players_runs:
            if pl_id == 8 and cmp.map.code != "MLXXXBA":
                continue

            if pl_id in cmp.players:
                players_runs[pl_id]["tot"] += 1
                if cmp.accepted_by is None:
                    players_runs[pl_id]["na"] += 1
                elif cmp.deleted_on is not None:
                    players_runs[pl_id]["del"] += 1
                elif cmp.map.deleted_on is not None:
                    players_runs[pl_id]["delmap"] += 1
                elif cmp.format == 2:
                    players_runs[pl_id]["fmt2"] += 1

    with open(bpath / "output.txt", "w") as fout:
        for pl_id in players_runs:
            fout.write(f"Player #{pl_id}: {players_runs[pl_id]}\n")
