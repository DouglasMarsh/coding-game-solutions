import sys
import math
from collections import namedtuple
from typing import Callable


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
        self.distance_to_base = math.dist(base_pos, self.position)

        self.turns_to_base = self.distance_to_base / 400 if threat_for == 1 else sys.maxsize

    def __repr__(self) -> str:
        return f"s:{self._id} x:{self.position.x} y:{self.position.y} dist:{self.distance_to_base}"

class Hero:
    defend_pos: Point
    ignore_func:Callable[[Spider], bool]

    def __init__(self, _id: int, position: Point):
        self._id = _id
        self.position = position
        self.distance_to_base = math.dist(base_pos, self.position)
        self.target = 0
        self.ignore_func = lambda s: False

   
def defend(h:Hero):
    close_spiders = hero_spiders.get(h._id, [])
    if len(close_spiders) > 3:
        print(f"SPELL WIND {op_base_pos.x} {op_base_pos.y}")
        return
    
    #push ultra spiders
    s = next((s for s in ultra_spiders if s.distance_to_base < 1600 and math.dist(s.position, h.position) < 1000), None)
    if s and mana >= 10 :        
        print(f"SPELL WIND {op_base_pos.x} {op_base_pos.y}")
        return
    
    if len( critical_spiders) > 0:
        # attack spider closest
        s = critical_spiders[0]
        print(f"MOVE {s.position.x} {s.position.y}")
        return

    print(f"MOVE {h.defend_pos.x} {h.defend_pos.y}")

def attack(h:Hero):
    
    close_spiders = hero_spiders.get(h._id, [])
    if math.dist(h.position, op_base_pos) < 6000:
        if len(close_spiders) > 0:            
            print(f"SPELL WIND {op_base_pos.x} {op_base_pos.y}")
            return
        else:
            print(f"MOVE {h.defend_pos.x} {h.defend_pos.y}")
            return
    
    if len(close_spiders) > 3:
        print(f"SPELL WIND {op_base_pos.x} {op_base_pos.y}")
        return

    dS = next((s for s in close_spiders if s.threat_for == 1), None) or \
         next((s for s in dangerous_spiders if not s.near_base and not h.ignore_func(s)), None)
    tS = spiders.get(h.target, None)
        
    
    if dS:
        if tS and tS in dangerous_spiders:
            print(f"MOVE {tS.position.x} {tS.position.y}")
            return
        
        if dS in critical_spiders and math.dist(h.position, dS.position) < 4000:
            h.target = dS._id
            print(f"MOVE {dS.position.x} {dS.position.y}")
            return
    
    if tS:
        print(f"MOVE {tS.position.x} {tS.position.y}")
        return
    
    h.target = 0

    if len( spiders ) > 0 :
        ss = [ v for v in sorted(spiders.values(), key=lambda s: math.dist(h.position, s.position))]
        for s in ss:
            if not h.ignore_func(s):
                if mana >= 20:
                    if math.dist(h.position, s.position) < 1200 and math.dist(s.position, op_base_pos) < 10000:
                        print(f"SPELL WIND {op_base_pos.x} {op_base_pos.y}")
                        return
                elif math.dist(h.position, s.position) < 4000:
                    h.target = s._id                
                    print(f"MOVE {s.position.x} {s.position.y}")
                    return
                else:               
                    print(f"MOVE {s.position.x} {s.position.y}")
                    return
                    
    
    if len(critical_spiders) > 0:
        cs = critical_spiders[-1]
        print(f"MOVE {cs.position.x} {cs.position.y}")
        return

    print(f"MOVE {h.defend_pos.x} {h.defend_pos.y}")


# Auto-generated code below aims at helping you parse
# the standard input according to the problem statement.

# base x,y: The corner of the map representing your base
bX, bY = map(int, input().split())
oX,oY = (0,0)
oX = 17630 if bX == 0 else 0
oy = 9000 if bY == 0 else 0

base_pos:Point = Point( bX, bY)
op_base_pos:Point = Point( oX, oY)

heroes_per_player = int(input())  # Always 3
heros: dict[int, Hero] = {}
op_heros: dict[int, Hero] = {}


# game loop
while True:

    spiders: dict[int, Spider] = {}
    dangerous_spiders: list[Spider] = []
    critical_spiders: list[Spider] = []
    ultra_spiders: list[Spider] = []

    hero_spiders: dict[int, list[Spider]] = {}

    # health: Each player's base health
    # mana: Ignore in the first league; Spend ten mana to cast a spell
    health, mana = [int(j) for j in input().split()]
    op_health, op_mana = [int(j) for j in input().split()]
            
        
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
            spiders[_id] = s

            if threat_for == 1:
                dangerous_spiders.append(s)
                if near_base == 1:
                    critical_spiders.append(s)
                    if s.health/2 > s.turns_to_base:
                        ultra_spiders.append(s)

        elif _type == 1:
            if not _id in heros:
                heros[_id] = Hero(_id, Point(x,y))                   
            else:
                heros[_id].position = Point(x,y)


        elif _type == 2:
            if not _id in op_heros:
                op_heros[_id] = Hero(_id, Point(x,y))
            else:
                op_heros[_id].position = Point(x,y)

    idx = 0
    for h in heros.values():
        if idx == 0:
            h.defend_pos = h.position
        elif idx == 1:            
            h.defend_pos = Point(8500, 1500)
            h.ignore_func = lambda s: s.position.y > 5000
        elif idx == 2:
            h.defend_pos = Point(13000, 7500) if base_pos.x == 0 else Point(7000, 7500)
            h.ignore_func = lambda s: s.position.y < 4000
        
        idx += 1

    for s in spiders.values():
        for h in heros.values():
            if math.dist(s.position, h.position) < 1600:
                hero_spiders.setdefault(h._id,[]).append(s) 

    
    dangerous_spiders.sort( key=lambda s: s.turns_to_base)
    critical_spiders.sort( key=lambda s: s.turns_to_base)
    ultra_spiders.sort( key=lambda s: s.turns_to_base)
    
    idx = 0
    for h in heros.values():
        if idx == 0:
            defend(h)
        else:
            attack(h)
        
        idx += 1

        
        

   

        # Write an action using print
        # To debug: print("Debug messages...", file=sys.stderr, flush=True)


        # In the first league: MOVE <x> <y> | WAIT; In later leagues: | SPELL <spellParams>;
        # print("WAIT")
