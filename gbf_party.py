class Character:
    def __init__(self, position, name, maxhp, img, id):
        self.pos = position
        self.name = name
        self.max_hp = maxhp
        self.hp = maxhp
        self.img = img
        self.img_id = id
        self.total_dmg_dealt = 0
        self.dmg_done_list = list()

    def get_name(self):
        return self.name

    def get_pos(self):
        return self.pos

    def get_img(self):
        return self.img

    def get_hp(self):
        return self.hp

    def is_dead(self):
        return self.hp <= 0

    def set_hp(self, hp):
        self.hp = hp

    def get_total_dmg(self):
        return self.total_dmg_dealt

    def deal_dmg(self, dmg):
        self.dmg_done_list.append(dmg)
        self.total_dmg_dealt = self.total_dmg_dealt + dmg

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

class Party:
    def __init__(self, chars: list[Character], summons: list[Summon]):
        self.members = chars
        self.summons = summons

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
