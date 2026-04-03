import json
import time
from gbf_asset_requestor import scrape_raid_info

class RaidInfo:
    def __init__(self, name, at, maxhp, img, id):
        self.name = name
        self.max_hp = maxhp
        self.hp = maxhp
        self.img = img
        self.img_id = id
        self.attribute = at
        if self.name != "":
            self.boss_info = scrape_raid_info(self.name)

    def get_name(self):
        return self.name

    def get_img(self):
        return self.img

    def get_hp(self):
        return self.hp

    def get_max_hp(self):
        return self.max_hp

    def set_hp(self, hp):
        self.hp = hp

    def get_attribute(self):
        return self.attribute

    def get_effect_table(self):
        return self.boss_info

class Character:
    def __init__(self, position, name, maxhp, img, id):
        self.pos = position
        self.name = name
        self.max_hp = maxhp
        self.hp = maxhp
        self.img = img
        self.img_id = id

        self.auto_dmg = 0
        self.ougi_dmg = 0
        self.skill_dmg = 0
        self.total_dmg = 0

        self.total_dmg_dealt = 0
        self.total_heal_done = 0
        self.heal_done_dict = {}
        self.dmg_done_dict = {}

    def get_name(self):
        return self.name

    def get_pos(self):
        return self.pos

    def get_img(self):
        return self.img

    def get_id(self):
        return self.img_id

    def get_hp(self):
        return self.hp

    def is_dead(self):
        return self.hp <= 0

    def set_hp(self, hp):
        self.hp = hp

    def heal(self, hp: int, turn: int):
        self.heal_done_dict.setdefault(turn, []).append(hp)
        self.total_heal_done += hp

    def get_total_heal_done(self):
        return self.total_heal_done

    def get_heal_list(self, key: int) -> list[int]:
        return self.heal_done_dict.get(key, [])

    def deal_dmg(self, dmg: int, turn: int, category="auto",):
        self.dmg_done_dict.setdefault(turn, []).append(dmg)
        if category == "auto":
            self.auto_dmg += dmg
        elif category == "ougi":
            self.ougi_dmg += dmg
        elif category == "skill":
            self.skill_dmg += dmg

        self.total_dmg_dealt = self.total_dmg_dealt + dmg

    def get_total_dmg(self):
        return self.total_dmg_dealt
    
    def get_dmg_list(self, key: int) -> list[int]:
        return self.dmg_done_dict.get(key, [])

    def get_breakdown(self) -> dict[str, int]:
        return {
            "Autos": self.auto_dmg,
            "Ougi": self.ougi_dmg,
            "Skills": self.skill_dmg
        }

class Summon:
    def __init__(self, position, name, cd, img, id):
        self.pos = position
        self.name = name
        self.cooldown = cd
        self.img = img
        self.img_id = id

    def get_name(self):
        return self.name

    def get_pos(self):
        return self.pos

    def get_img(self):
        return self.img

class Item:
    def __init__(self, position, img, id):
        self.pos = position
        self.img = img
        self.img_id = id

    def get_pos(self):
        return self.pos

    def get_img(self):
        return self.img


class Party:
    def __init__(self, chars: list[Character], summons: list[Summon], items: list[Item]):
        self.members = chars
        self.summons = summons
        self.items = items

    def __getitem__(self, key) -> Character:
        try:
            return self.members[key]
        except IndexError:
            raise IndexError(f"Member index {key} is out of range (0-{len(self.members)-1})")

    def get_items(self) -> list[Item]:
        return self.items
    
    def get_summon(self, key) -> Summon:
        try:
            return self.summon[key]
        except IndexError:
            raise IndexError(f"Summon index {key} is out of range (0-{len(self.summon)-1})")

    def export_to_json(self, indent=2) -> str:
        party_data = {
            "members": [
                {
                    "position": c.pos,
                    "name": c.name,
                    "damage_stats": {
                        "total": c.total_dmg_dealt,
                        "autos": c.auto_dmg,
                        "ougi": c.ougi_dmg,
                        "skills": c.skill_dmg,
                        "breakdown_per_turn": c.dmg_done_dict
                    },
                    "heal_stats": {
                        "total": c.total_heal_done,
                        "breakdown_per_turn": c.heal_done_dict
                    }
                } for c in self.members
            ],
            "summons": [
                {
                    "position": s.pos,
                    "name": s.name,
                    "cooldown": s.cooldown,
                    "img_id": s.img_id
                } for s in self.summons
            ],
            "grid": [
                {
                    "position": item.get_pos(),
                    "item_img": item.get_img()
                } for item in self.get_items()
            ]
        }
        return json.dumps(party_data, indent=2)

    def __setitem__(self, key, value):
        self.members[key] = value

    def get_members_list(self) -> list[Character]:
        return self.members

    def get_summon_list(self) -> list[Summon]:
        return self.summons


    def get_member_names(self):
        for mem in self.members:
            print(mem.get_name())

class Quest:
    def __init__(self, raid: RaidInfo, party: Party, quest_id: int, turn = 0):
        self.raid = raid
        self.quest_id = quest_id
        self.party = party
        self.turn = turn
        self.finished = False
        self.start_time = time.monotonic()

    def get_raid(self) -> RaidInfo:
        return self.raid

    def get_quest_id(self):
        return self.quest_id
    
    def get_party(self) -> Party:
        return self.party

    def finish_quest(self):
        self.finished = True

    def get_turn(self):
        return self.turn

    def set_turn(self, turn: int):
        if turn > self.turn:
            self.turn = turn

    def get_elapsed_time(self):
        return time.monotonic() - self.start_time

    def get_minutes_passed(self):
        return (int(self.get_elapsed_time() // 60) + 1)
