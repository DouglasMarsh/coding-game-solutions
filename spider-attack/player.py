import sys
import math
import random as rnd
from collections import namedtuple
from typing import Callable
  
Point = namedtuple("Point", "x y")
Vector = namedtuple("Vector", "x y")
InRangeSpiders = namedtuple("InRangeSpiders", "attack wind control")

class Spider:
    def __init__(self, _id: int, pos: Point , health: int, trajectory: Vector, near_base: bool, threat_for: int, shield_life: int, is_controlled: bool):
        self._id = _id
        self.position = pos
        self.health = health
        self.trajectory = trajectory
        self.near_base = near_base
        self.threat_for = threat_for
        self.distance_to_base = math.dist(base_pos, self.position)
        self.shield_life = shield_life
        self.is_controlled = is_controlled

        self.turns_to_base = self.distance_to_base / 400 if threat_for == 1 else sys.maxsize

    def __repr__(self) -> str:
        return f"s:{self._id} x:{self.position.x} y:{self.position.y} dist:{self.distance_to_base}"

class Hero:
    defend_pos: Point
    ignore_func:Callable[[Spider], bool]

    def __init__(self, _id: int, position: Point, trajectory: Vector, shield_life: int, is_controlled: bool):
        self._id = _id
        self.name = ""
        self.position = position
        self.trajectory = trajectory
        self.distance_to_base = math.dist(base_pos, self.position)
        self.target = 0
        self.ignore_func = lambda s: False
        self.shield_life = shield_life
        self.is_controlled = is_controlled

    def wait(self) -> str:
        print( f"WAIT {self.name}" )
    def move(self, p:Point):
        print( f"MOVE {p.x} {p.y} {self.name}" )
    def wind(self, p:Point):
        global mana
        mana -= 10
        print( f"SPELL WIND {p.x} {p.y} {self.name}" )
        
    def control(self, id:int, p:Point):
        global mana
        mana -= 10
        print( f"SPELL CONTROL {id} {p.x} {p.y} {self.name}" )
    def shield(self, id:int):
        global mana
        mana -= 10
        print( f"SPELL SHIELD {id} {self.name}" )

def spider_in_range(heros:list[Hero], s: Spider) -> Hero | None:
    for h in heros:
        if math.dist(s.position, h.position) <= 800:
            return h
    
    return None

def move_to(f: Point, t: Point, step: int) -> Point:
    dx = t.x - f.x
    dy = t.y - f.y
    dist = math.sqrt(dx*dx + dy*dy)
    nx = dx/dist
    ny = dy/dist

    return Point(int(f.x + nx*step), int(f.y + ny*step))

def add_vector(p: Point, v: Vector) -> Point:
    return Point(p.x + v.x, p.y + v.y)
def approaching_base(b: Point, p:Point, t: Vector) -> bool:
    d = Point(p.x + t.x, p.y + t.y)
    return math.dist(b, p) < math.dist(b, d)

def farm(h:Hero):
    hero_spiders:InRangeSpiders = hero_spiders_map.get(h._id, InRangeSpiders([],[],[]))

    if len( hero_spiders.control ) > 0 :
        tS = spiders.get(h.target, None)
        if tS and tS in hero_spiders.control:
            p = add_vector(tS.position, tS.trajectory)
            h.move(p)
            return

        cluster = (hero_spiders.control[0], 1)
        for s in hero_spiders.control:
            cnt = len([x for x in hero_spiders.control if math.dist(x.position, s.position) <= 800])
            if cnt > cluster[1]:
                cluster = (s,cnt)
        
        tS = cluster[0]
        h.target = tS._id
        p = add_vector(tS.position, tS.trajectory)
        h.move(p)
        return
                    
            
    dx = h.defend_pos.x + rnd.randint(0,1200)
    dy = h.defend_pos.y + rnd.randint(0,1200)
    h.move( Point(dx, dy))
    return

def defend(h:Hero):
    hero_spiders:InRangeSpiders = hero_spiders_map.get(h._id, InRangeSpiders([],[],[]))

    if len(ultra_spiders) > 0:
        wind_ultra = set(hero_spiders.wind).intersection(ultra_spiders)
        if mana >= 10 and len( [s for s in wind_ultra if s.shield_life == 0]) > 0:
            h.wind(op_base_pos)
            return

        h.move( move_to(ultra_spiders[0].position, base_pos, 400) )  
        return

    if len( critical_spiders) > 0:
        h.move( move_to(critical_spiders[0].position, base_pos, 400) )  
        return

    if turn > 100:
        oH = next((oH for oH in op_heros.values() if math.dist(oH.position, base_pos) < 5800 and math.dist(oH.position,h.position) < 2200), None)
        if oH:
            h.control(oH._id, op_base_pos)
            return
    else:
        danger_close = set(hero_spiders.wind).intersection(dangerous_spiders)
        if len(danger_close) > 0:
            h.move( move_to(danger_close.pop().position, base_pos, 400) ) 
            return
           
    if h.position == h.defend_pos:
        h.wait()
        return
    
    h.move( h.defend_pos )
    return

def attack(h:Hero):
    hero_spiders:InRangeSpiders = hero_spiders_map.get(h._id, InRangeSpiders([],[],[]))

    if turn > 90: 
        h.defend_pos = move_to(op_base_pos, base_pos, 5000)
        if math.dist(h.position, h.defend_pos) > 3200:
           h.move( h.defend_pos)
           return
        
        if mana > 20:
            if len(op_ultra_spiders) > 0:
                uS = next((s for s in op_ultra_spiders if s.shield_life == 0), None)
                if uS:
                    h.shield(uS._id)
                    return                    
                
            if len(op_critical_spiders) > 0:
                shielded = [s for s in op_critical_spiders if s.shield_life > 0]
                if len(shielded) > 3:
                    oH = next(oH for oH in op_heros.values() if math.dist(oH.position, op_base_pos) < 6900)
                    if oH:
                        h.control(oH._id, base_pos)
                        return
                    
                cS = next((s for s in op_critical_spiders if s.shield_life == 0), None)
                if cS:
                    h.shield(cS._id)
                    return

            if len(hero_spiders.wind) > 0:
                if len([s for s in hero_spiders.wind if s.shield_life == 0 and math.dist(s.position, op_base_pos) <= 7000]) > 0:
                    h.wind(op_base_pos)
                    return
            
            if len(hero_spiders.control) > 0:
                s = next((s for s in hero_spiders.control if s.threat_for != 2), None)
                if s:
                    h.control(s._id, op_base_pos)
                    return
    else:
        farm(h)
        return            
            
    dx = h.defend_pos.x + rnd.randint(0,1200)
    dy = h.defend_pos.y + rnd.randint(0,1200)
    h.move( Point(dx, dy))
    return

def prevent(h: Hero) -> bool:

    def dangerZone(oH:Hero) -> bool:
        return approaching_base(base_pos, oH.position, oH.trajectory) \
            or math.dist(base_pos, oH.position) <= 6800

    if turn > 100:
        oH = next((oH for oH in sorted(op_heros.values(), key=lambda h: math.dist(base_pos, h.position)) if dangerZone(oH) ), None)
        if oH :
            if oH.shield_life == 0 :
                if math.dist(oH.position, h.position) <= 2200:
                    h.control(oH._id, op_base_pos)
                    return True
            else :
                p = add_vector(oH.position, oH.trajectory)
                h.move(p)
                return True
            
    return False


# base x,y: The corner of the map representing your base
bX, bY = map(int, input().split())
oX,oY = (0,0)
oX = 17630 if bX == 0 else 0
oY = 9000 if bY == 0 else 0

base_pos:Point = Point( bX, bY)
op_base_pos:Point = Point( oX, oY)

heroes_per_player = int(input())  # Always 3
heros: dict[int, Hero] = {}
op_heros: dict[int, Hero] = {}


DEFENDER = "DEFENDER"
SAFETY = "SAFETY"
ATTACKER = "ATTACKER"
positions = {
    0: move_to(base_pos, op_base_pos, 5000),
    1: Point(8500, 1500),
    2: Point(9500, 7500) if base_pos.x == 0 else Point(7500, 7500)
}
ignore_funcs = {
    0: lambda s: False,
    1: lambda s: s.position.y > 5000,
    2: lambda s: s.position.y < 5000,
}
role = {}

turn = 0
health, mana = [3,0]
op_health, op_mana = [3,0]

# game loop
while True:
    turn += 1

    spiders: dict[int, Spider] = {}
    dangerous_spiders: list[Spider] = []
    critical_spiders: list[Spider] = []
    ultra_spiders: list[Spider] = []

    hero_spiders_map: dict[int, InRangeSpiders] = {}
    
    op_dangerous_spiders: list[Spider] = []
    op_critical_spiders: list[Spider] = []
    op_ultra_spiders: list[Spider] = []

    # health: Each player's base health
    # mana: Ignore in the first league; Spend ten mana to cast a spell
    health, mana = [int(j) for j in input().split()]
    op_health, op_mana = [int(j) for j in input().split()]
    
    hIdx = 0
    entity_count = int(input())  # Amount of heros and monsters you can see
    for i in range(entity_count):
        # _id: Unique identifier
        # _type: 0=monster, 1=your hero, 2=opponent hero
        # x: Position of this entity
        # shield_life: Ignore for this league; Count down until shield spell fades
        # is_controlled: Ignore for this league; Equals 1 when this entity is under a control spell
        # health: Remaining health of this monster
        # vx: Trajectory of this monster
        # near_base: 0=monster with no target yet, 1=monster targeting a base
        # threat_for: Given this monster's trajectory, is it a threat to 1=your base, 2=your opponent's base, 0=neither
        _id, _type, x, y, shield_life, is_controlled, health, vx, vy, near_base, threat_for = [int(j) for j in input().split()]

        if _type == 0:
            
            s = Spider( _id, Point(x,y), health, Vector(vx,vy), near_base == 1, threat_for, shield_life, is_controlled == 1 )
            spiders[_id] = s

            if threat_for == 1:
                dangerous_spiders.append(s)
                if near_base == 1:
                    critical_spiders.append(s)
                    if s.health/2 > s.turns_to_base:
                        ultra_spiders.append(s)
            elif threat_for == 2:
                op_dangerous_spiders.append(s)
                if near_base == 1:
                    op_critical_spiders.append(s)
                    if s.health/2 > s.turns_to_base:
                        op_ultra_spiders.append(s)

        elif _type == 1:
            if not _id in heros:

                heros[_id] = Hero(_id, Point(x,y), Vector(vx,vy), shield_life, is_controlled == 1)
                heros[_id].defend_pos = positions[hIdx]
                heros[_id].ignore_func = ignore_funcs[hIdx]
                role[hIdx] = _id

                print(f"Init hero {_id} in role {hIdx}", file=sys.stderr, flush=True)
                hIdx += 1
            else:
                heros[_id].position = Point(x,y)
                heros[_id].trajectory = Vector(vx,vy)
                heros[_id].shield_life = shield_life
                heros[_id].is_controlled = is_controlled == 1

        elif _type == 2:
            if not _id in op_heros:
                op_heros[_id] = Hero(_id, Point(x,y), Vector(vx,vy), shield_life, is_controlled == 1)
            else:
                op_heros[_id].position = Point(x,y)
                op_heros[_id].trajectory = Vector(vx,vy)
                op_heros[_id].shield_life = shield_life
                op_heros[_id].is_controlled = is_controlled == 1

        
    
    for s in spiders.values():
        for h in heros.values():
            if math.dist(s.position, h.position) <= 2200:
                hero_spiders_map.setdefault(h._id,InRangeSpiders([],[],[])).control.append(s) 
            if math.dist(s.position, h.position) <= 1280:
                hero_spiders_map.setdefault(h._id,InRangeSpiders([],[],[])).wind.append(s) 
            if math.dist(s.position, h.position) <= 800:
                hero_spiders_map.setdefault(h._id,InRangeSpiders([],[],[])).attack.append(s) 
    
    dangerous_spiders.sort( key=lambda s: s.turns_to_base)
    critical_spiders.sort( key=lambda s: s.turns_to_base)
    ultra_spiders.sort( key=lambda s: s.turns_to_base)

    for h in heros.values():
        
        if role[0] == h._id:
            h.name = DEFENDER
            if turn > 75: h.defend_pos = move_to(base_pos, op_base_pos, 2000)
            defend(h)
        elif role[1] == h._id:
            h.name = SAFETY
            if turn < 90:
                attack(h)
            else:
                h.defend_pos = move_to(base_pos, op_base_pos, 5000)
                if not prevent(h): defend(h)
        else:
            h.name = ATTACKER
            attack(h)

        # Write an action using print
        # To debug: print("Debug messages...", file=sys.stderr, flush=True)

