import json
from dataclasses import dataclass
from gbf_asset_requestor import wiki_dl_char, wiki_dl_summon
from typing import Any, Dict
from gbf_party import Party, Character, Summon, RaidInfo, Quest
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

    def parse(self) -> Quest:
        try:
            raidinfo = self._parse_raid()
            members = self._parse_members()
            summons = self._parse_summons()
            p = Party(members, summons)
            quest = Quest(raidinfo, p)
        except Exception as e:
            print(e)
        return quest

    def set_data(self, json_data: Dict[str, Any]):
        self.data = json_data

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
            raid_name = boss_data.get('name', {}).get('en', "Unknown Raid")
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
        asset_ids = self.get_asset_id()

        for i, member in enumerate(party_members):
            if i >= party_members_number:
                break

            char_pid = str(member.get("pid", ""))

            found = False
            for filename in asset_ids:
                if char_pid in filename:
                    img_path = f"./db/{filename}.jpg" 
                    found = True
                    break

            if not found:
                img_path = wiki_dl_char(char_pid)
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

            asset_ids = self.get_asset_id()
            for i, s in enumerate(summs):
                summon_id = str(s.get("image_id", ""))
                if not summon_id:
                    continue

                img_path = None
                found = False
                for filename in asset_ids:
                    if summon_id in filename:
                        img_path = f"./db/{filename}.jpg"
                        found = True
                        break
                if not found:
                    img_path = wiki_dl_summon(summon_id)

                summon = Summon(
                    position=i,
                    name=s.get("name"),
                    cd=s.get("require"),
                    img = img_path,
                    id = summon_id
                )    
                summons.append(summon)

            friend_summ = self.data.get("supporter")
            friend_summ_name=friend_summ.get("name"),
            friend_summ_id = friend_summ.get("image_id")
            cooldown=friend_summ.get("require")
            friend_img_path = ""
            for filename in asset_ids:
                if friend_summ_id in filename:
                    friend_img_path = f"./db/{filename}.jpg"
                    found = True
                    break

            if not found:
                friend_img_path = wiki_dl_summon(friend_summ_id)

            summon = Summon(
                position=5,
                name=friend_summ_name,
                cd=cooldown,
                img=friend_img_path,
                id=friend_summ_id
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
                party_member.deal_dmg(dmg_dealt)
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
                party_member.deal_dmg(dmg_dealt)
                print(f"Loop damage {party_member.get_name()}: {dmg_dealt}")

    def _parse_ougi(self, action, party: Party):
        attacker_idx = action.get("pos", 0)
        party_member = party[attacker_idx]
        dmg_payload = action.get("list", [])
        for entry in dmg_payload:
            hits = entry.get("damage", [])
            for hit in hits:
                dmg_val = int(hit.get("value", 0))
                party_member.deal_dmg(dmg_val, "ougi")
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
            party[top_ability.pos].deal_dmg(dmg_dealt, "skill")
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
