import json
from dataclasses import dataclass
from gbf_asset_requestor import download_asset
from typing import Any, Dict
from gbf_party import Party, Character, Summon, RaidInfo, Quest, Item
import os
from pathlib import Path

@dataclass
class Ability:
    name: str
    pos: int

class Parser:
    def __init__(self, json_data: Dict[str, Any]) -> None:
        self.data = json_data
        self.ability_queue = list()
        self.combat_log = list()
        self.active_turn = 0
        self.items = None

    def parse(self) -> Quest:
        try:
            turn = self._parse_turn()
            raidinfo = self._parse_raid()
            members = self._parse_members()
            summons = self._parse_summons()
            items = self._parse_items()
            if items:
                self.items = items
            p = Party(members, summons, self.items)
            quest_id = self.data.get("raid_id", "")
            quest = Quest(raidinfo, p, quest_id, turn)
        except Exception as e:
            print(f"Error in parse {e}")
        return quest

    def set_data(self, json_data: Dict[str, Any]):
        self.data = json_data

    def _parse_items(self):
        deck_list = self.data.get("deck_list", {})
        items = []
        try:
            for key, val in deck_list.items():
                weapons = val.get("weapon", {})
                for k, v in weapons.items():
                    pos = int(k)
                    weapon_id = v.get("weapon_id", "")
                    image_id = v.get("image_id", "")
                    if not image_id or str(image_id).lower() == "none":
                        continue
                    expected_filename = f"weapon_{image_id}.png"
                    img_path = f"./db/{expected_filename}"

                    if not os.path.exists(img_path):
                        img_path = download_asset(image_id, "weapon")
                   
                    item = Item(
                        position = pos,
                        img = image_id,
                        id = weapon_id
                    )
                    items.append(item)
                break
        except Exception as e:
            print(e)
        return items

    def _parse_turn(self) -> int:
        return self.data.get("turn", 0)

    def _update_raid(self, raid_info: RaidInfo, data_chunk):
        if isinstance(data_chunk, dict):
            if "hp" in data_chunk:
                raid_info.set_hp(data_chunk["hp"])
            for v in data_chunk.values():
                self._update_raid(raid_info, v)
        elif isinstance(data_chunk, list):
            for item in data_chunk:
                self._update_raid(raid_info, item)

    def parse_damage(self, quest: Quest):
        party = quest.get_party()
        raid_info = quest.get_raid()
        quest.set_turn(self._parse_turn())
        self.active_turn = quest.get_turn()
        print(f"Quest: {quest.get_turn()}")
        try:
            if not party or len(party.members) == 0:
                return

            scenario = self.data.get("scenario")
            if not scenario or not isinstance(scenario, list):
                return
            try:
                for action in scenario:
                    if not isinstance(action, dict):
                        continue
                    action_type = action.get("cmd")
                    # LOOK IF THERE IS A SWAP TO CHANGE PLAYER IN MAIN PARTY
                    # USE DARK TEAM TO DEBUG AS DANUA HAS A SWAP
                         
                    if action.get("from") == "player" or action.get("to") == "boss":
                        self._update_raid(raid_info, action)

                    if action_type in ["attack", "special", "special_npc", "turn", "ability"]:
                        self.ability_queue.clear()

                    if action_type == "attack" and action.get("from") == "player":
                        self._parse_normal_attack(action, party)

                    elif action_type == "ability":
                        self._record_ability(action)

                    elif action_type == "damage" and action.get("to") == "boss":
                        self._parse_single_hit_ability(action, party)

                    elif action_type in ["special", "special_npc"]:
                        self._parse_ougi(action, party)

                    elif action_type == "loop_damage" and action.get("to") == "boss":
                        self._parse_loop_damage(action, party)

                    elif action_type == "die" and action.get("to") == "player":
                        self._parse_dead_character(action, party)
            except Exception as e:
                print(f"{action}")
                print(e)

        except Exception as e:
            print(f"Failed to parse damage {e}")

        print("---------------------------------------------")

    def get_inventory() -> None:
        
        pass

    def parse_combat_log(self) -> None:

        pass

    def add_combat_log(self, log: str) -> None:
        self.combat_log.append(log) 
        pass


    def get_asset_id(self) -> list[str]:
        path = Path("./db")
        return [f.stem for f in path.iterdir() if f.is_file()]

    def _parse_raid(self) -> RaidInfo:
        try:
            boss_data = self.data.get('boss', {}).get('param', [{}])[0]
            raid_name = boss_data.get('name', {}).get('en', "")
            current_hp = int(boss_data.get('hp', 0))
            max_hp = int(boss_data.get('hpmax', 1))
            img_id = boss_data.get("enemy_id")
            attribute = boss_data.get("attribute")

            raid = RaidInfo(
                name = raid_name,
                at = attribute,
                maxhp = max_hp,
                id = img_id,
                img = id # this doesnt work for now
            )
            return raid

        except Exception as e:
            print(f"Failed to parse raid {e}")

        return None

    def _parse_members(self) -> list[Character]:
        characters = list()
        player = self.data.get("player")
        if not player or not isinstance(player, dict):
            return None

        party_members = player.get("param", [])
        party_members_number = player.get("number", 0)

        for i, member in enumerate(party_members):
            if i >= party_members_number:
                break

            char_pid = str(member.get("pid_image", ""))
            expected_filename = f"char_{char_pid}.png"
            img_path = f"./db/{expected_filename}"

            if not os.path.exists(img_path):
                img_path = download_asset(char_pid, "char")

            try:
                char = Character(
                    name=member.get("name", "Unknown"),
                    position=i,
                    maxhp=member.get("hpmax", 0),
                    id=char_pid,
                    img=img_path,
                )
                characters.append(char)
            except Exception as e:
                print(f"Error parsing member {i}: {e}")
                continue
        return characters
      

    def _parse_summons(self) -> list[Summon]:
        summons = list()
        try:
            summs = self.data.get("summon")
            if not summs or not isinstance(summs, list):
                return None

            for i, s in enumerate(summs):
                summon_id = str(s.get("image_id", ""))
                if not summon_id:
                    continue

                expected_filename = f"summon_{summon_id}.png"
                img_path = f"./db/{expected_filename}"

                if not os.path.exists(img_path):
                    img_path = download_asset(summon_id, "summon")

                summon = Summon(
                    position=i,
                    name=s.get("name"),
                    cd=s.get("require"),
                    img = img_path,
                    id = summon_id
                )    
                summons.append(summon)

            supporter = self.data.get("supporter")
            if supporter:
                friend_id = str(supporter.get("image_id", ""))
                friend_name = supporter.get("name")

                expected_filename = f"summon_{friend_id}.png"
                img_path = f"./db/{expected_filename}"

                if not os.path.exists(img_path):
                    img_path = download_asset(friend_id, "summon")

                summon = Summon(
                    position=5,
                    name=supporter.get("name"),
                    cd=supporter.get("require"),
                    img=img_path,
                    id=friend_id
                )
                summons.append(summon)

            
        except Exception as e:
            print(f"Couldn't parse summons with error {e}")

        return summons

    def _parse_normal_attack(self, action, party: Party):
        attacker_idx = action.get("pos") 
        party_member = party[attacker_idx]

        dmg_payload = action.get("damage")
        sequences = []
        if isinstance(dmg_payload, list):
            sequences = dmg_payload
        elif isinstance(dmg_payload, dict):
            sequences = dmg_payload.values()
        
        for hit_sequence in sequences:
            if not isinstance(hit_sequence, list):
                continue
            for hit in hit_sequence:
                dmg_dealt = int(hit.get("value", 0))
                party_member.deal_dmg(dmg_dealt, self.active_turn)
                print(f"Normal attack {party_member.get_name()}: {dmg_dealt}")

    def _record_ability(self, action):
        abil_name = action.get("name", "")
        abil_pos = action.get("pos", 0)
        abil = Ability(
            name = abil_name,
            pos = abil_pos
        )
        self.ability_queue.append(abil)

    def _parse_loop_damage(self, action, party: Party):
        attacker_idx = action.get("total")[0]["pos"]
        party_member = party[attacker_idx]
        dmg_payload = action.get("list", [])

        sequences = []
        if isinstance(dmg_payload, list):
            sequences = dmg_payload
        elif isinstance(dmg_payload, dict):
            sequences = dmg_payload.values()

        for hit_sequence in sequences:
            if not isinstance(hit_sequence, list):
                continue
            for hit in hit_sequence:
                dmg_dealt = int(hit.get("value", 0))
                party_member.deal_dmg(dmg_dealt, self.active_turn)
                print(f"Loop damage {party_member.get_name()}: {dmg_dealt}")

    def _parse_ougi(self, action, party: Party):
        attacker_idx = action.get("pos", 0)
        party_member = party[attacker_idx]
        dmg_payload = action.get("list", [])
        for entry in dmg_payload:
            hits = entry.get("damage", [])
            for hit in hits:
                dmg_val = int(hit.get("value", 0))
                party_member.deal_dmg(dmg_val, self.active_turn, "ougi")
                print(f"Ougi {party_member.get_name()}: {dmg_val}")

    def _parse_single_hit_ability(self, action, party: Party):
        if not self.ability_queue:
            return

        hits = action.get("list", [])
        top_ability = self.ability_queue[0]

        if not action.get("turn_end"): #abilities that do plain dmg at the end
            self.ability_queue.pop(0)

        party_member = party[top_ability.pos]
        for hit in hits:
            dmg_dealt = int(hit.get("value", 0))
            party[top_ability.pos].deal_dmg(dmg_dealt, self.active_turn, "skill")
            print(f"Single shot {party_member.get_name()}: {dmg_dealt}")

    def _parse_dead_character(self, action, party: Party):
        dead_pos = action.get("pos")
        party[dead_pos].set_hp(0)

        for i, member in enumerate(party.get_members_list()):
            if i < 4:
                continue
            if not member.is_dead():
                party[dead_pos], party[i] = party[i], party[dead_pos]
                party[dead_pos].pos = dead_pos  # the bench char now at front
                party[i].pos = i
                return
