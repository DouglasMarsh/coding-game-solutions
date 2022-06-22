from cmath import sqrt
import sys
import math
from collections import namedtuple

Point = namedtuple("Point", "x y")
Vector = namedtuple("Vector", "x y")

class Spider:
    def __init__(self, _id: int, pos: Point , health: int, trajectory: Vector, near_base: bool, threat_for: int):
        self._id = _id
        self.position = pos
        self.health = health
        self.trajectory = trajectory
        self.near_base = near_base
        self.threat_for = threat_for
        self.distance_to_base = math.dist(base_pos, self.position) if threat_for == 1 else sys.maxsize

    def __repr__(self) -> str:
        return f"s:{self._id} x:{self.position.x} y:{self.position.y} dist:{self.distance_to_base}"

class Hero:
    def __init__(self, _id: int, position: Point):
        self._id = _id
        self.position = position

# Auto-generated code below aims at helping you parse
# the standard input according to the problem statement.

# base x,y: The corner of the map representing your base
base_pos:Point = tuple(map(int, input().split()))
heroes_per_player = int(input())  # Always 3

heros: dict[int, Hero] = {}

# game loop
while True:

    spiders: list[Spider] = []
    dangerous_spiders: list[Spider] = []

    for i in range(2):
        # health: Each player's base health
        # mana: Ignore in the first league; Spend ten mana to cast a spell
        health, mana = [int(j) for j in input().split()]
    entity_count = int(input())  # Amount of heros and monsters you can see
    for i in range(entity_count):
        # _id: Unique identifier
        # _type: 0=monster, 1=your hero, 2=opponent hero
        # x,y: Position of this entity
        # shield_life: Ignore for this league; Count down until shield spell fades
        # is_controlled: Ignore for this league; Equals 1 when this entity is under a control spell
        # health: Remaining health of this monster
        # vx,vy: Trajectory of this monster
        # near_base: 0=monster with no target yet, 1=monster targeting a base
        # threat_for: Given this monster's trajectory, is it a threat to 1=your base, 2=your opponent's base, 0=neither
        _id, _type, x, y, shield_life, is_controlled, health, vx, vy, near_base, threat_for = [int(j) for j in input().split()]

        if _type == 0:
            s = Spider( _id, Point(x,y), health, Vector(vx,vy), near_base == 1, threat_for )
            spiders.append( s )
            if threat_for == 1:
                dangerous_spiders.append(s)
                has_dangerous_spiders = True
                if s.near_base:
                    has_critical_spiders = True

        elif _type == 1:
            if not _id in heros:
                heros[_id] = Hero(_id, Point(x,y))
            else:
                heros[_id].position = Point(x,y)


    dangerous_spiders.sort( key=lambda s: s.distance_to_base)
    if len(dangerous_spiders) == 0:
        print("WAIT")
        print("WAIT")
        print("WAIT")
    else:
        print(dangerous_spiders, file=sys.stderr, flush=True)
        

        # hero 0 and 1 is responsible for critical spiders
        s = next((x for x in dangerous_spiders if  x.distance_to_base < 3000), None)
        if s == None:
            print("WAIT")
        else:
            print(f"MOVE {s.position.x} {s.position.y}")
        s = next((x for x in dangerous_spiders if  x.distance_to_base < 3000), None)
        if s == None:
            print("WAIT")
        else:
            print(f"MOVE {s.position.x} {s.position.y}")

        
        #hero 1 response for dangerous spiders not critical
        s = next((x for x in dangerous_spiders if  x.distance_to_base > 5000), None)
        if s == None:
            print("WAIT")
        else:
            print(f"MOVE {s.position.x} {s.position.y}")
        

   

        # Write an action using print
        # To debug: print("Debug messages...", file=sys.stderr, flush=True)


        # In the first league: MOVE <x> <y> | WAIT; In later leagues: | SPELL <spellParams>;
        # print("WAIT")
