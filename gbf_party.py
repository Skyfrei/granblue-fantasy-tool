class RaidInfo:
    def __init__(self, name, at, maxhp, img, id):
        self.name = name
        self.max_hp = maxhp
        self.hp = maxhp
        self.img = img
        self.img_id = id
        self.attribute = at

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
        self.heal_done_list = list()
        self.dmg_done_list = list()

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

    def heal(self, hp):
        self.heal_done_list.append(hp)
        self.total_heal_done += hp

    def get_total_heal_done(self):
        return self.total_heal_done

    def get_heal_list(self) -> list[int]:
        return self.heal_done_list


    def deal_dmg(self, dmg, category="auto"):
        self.total_dmg += dmg
        if category == "auto":
            self.auto_dmg += dmg
        elif category == "ougi":
            self.ougi_dmg += dmg
        elif category == "skill":
            self.skill_dmg += dmg

        # fix this maybe for log
        self.dmg_done_list.append(dmg)
        self.total_dmg_dealt = self.total_dmg_dealt + dmg

    def get_total_dmg(self):
        return self.total_dmg_dealt
    
    def get_dmg_list(self) -> list[int]:
        return self.dmg_done_list

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
    def __init__(self, position, name, cd, img, id):
        self.pos = position
        self.name = name
        self.img = img
        self.img_id = id

    def get_name(self):
        return self.name

    def get_pos(self):
        return self.pos

    def get_img(self):
        return self.img


class Party:
    def __init__(self, chars: list[Character], summons: list[Summon]):
        self.members = chars
        self.summons = summons
        #self.items = items

    def __getitem__(self, key) -> Character:
        try:
            return self.members[key]
        except IndexError:
            raise IndexError(f"Member index {key} is out of range (0-{len(self.members)-1})")
    
    def get_summon(self, key) -> Summon:
        try:
            return self.summon[key]
        except IndexError:
            raise IndexError(f"Summon index {key} is out of range (0-{len(self.summon)-1})")

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
    def __init__(self, raid: RaidInfo, party: Party):
        self.raid = raid
        self.party = party
        self.finished = False

    def get_raid(self) -> RaidInfo:
        return self.raid
    
    def get_party(self) -> Party:
        return self.party

    def finish_quest(self):
        self.finished = True

