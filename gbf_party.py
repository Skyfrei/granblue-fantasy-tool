class Character:
    def __init__(self, position, name, maxhp, img, id):
        self.pos = position
        self.name = name
        self.max_hp = maxhp
        self.hp = maxhp
        self.img = img
        self.img_id = id
        self.dmg_dealt = 0

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
        return self.dmg_dealt

    def deal_dmg(self, dmg):
        self.dmg_dealt = self.dmg_dealt + dmg

class Party:
    def __init__(self, chars: list[Character]):
        self.members = chars

    def __getitem__(self, key) -> Character:
        try:
            return self.members[key]
        except IndexError:
            raise IndexError(f"Member index {key} is out of range (0-{len(self.members)-1})")
    def __setitem__(self, key, value):
        self.members[key] = value

    def get_members_list(self) -> list[Character]:
        return self.members

    def get_member_names(self):
        for mem in self.members:
            print(mem.get_name())


