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
    was_controlled = False

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
        

    def wait(self, msg = ""):
        print( f"WAIT {self.name} {msg}" )
    def move(self, p:Point, msg = ""):
        print( f"MOVE {p.x} {p.y} {self.name} {msg}" )
    def wind(self, p:Point, msg = ""):
        global mana
        mana -= 10
        print( f"SPELL WIND {p.x} {p.y} {self.name} {msg}" )
        
    def control(self, id:int, p:Point, msg = ""):
        global mana
        mana -= 10
        print( f"SPELL CONTROL {id} {p.x} {p.y} {self.name} {msg}" )
    def shield(self, id:int, msg = ""):
        global mana
        mana -= 10
        print( f"SPELL SHIELD {id} {self.name} {msg}" )

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

    valid_targets = [s for s in hero_spiders.control if s not in op_critical_spiders]

    if len( valid_targets ) > 0 :
        tS = spiders.get(h.target, None)
        if tS and tS in valid_targets:
            p = add_vector(tS.position, tS.trajectory)
            h.move(p)
            return

        cluster = (valid_targets[0], 1)
        for s in valid_targets:
            cnt = len([x for x in valid_targets if math.dist(x.position, s.position) <= 800])
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

    if h.was_controlled and h.shield_life == 0:
        h.shield(h._id, "shield self")
        return

    if len(ultra_spiders) > 0:
        wind_ultra = set(hero_spiders.wind).intersection(ultra_spiders)
        if mana >= 10 and len( [s for s in wind_ultra if s.shield_life == 0]) > 0:
            h.wind(op_base_pos, "push too close")
            return


    if len( critical_spiders) > 0:
        tS = critical_spiders[0]
        h.move( move_to(tS.position, base_pos, 400), "atc CC"  )  
        return

    if len(dangerous_spiders) > 0:
        s = dangerous_spiders[0]
        h.move( add_vector(s.position, s.trajectory), "atk DGR" )
        return

    if len(hero_spiders.control) > 0:
        s = hero_spiders.control[0]
        h.move( add_vector(s.position, s.trajectory), "atk RS" )
        return

    if h.position == h.defend_pos:
        h.wait()
        return
    
    h.move( h.defend_pos, "move to DP" )
    return

def attack(h:Hero):
    hero_spiders:InRangeSpiders = hero_spiders_map.get(h._id, InRangeSpiders([],[],[]))

    if h.was_controlled and h.shield_life == 0 and mana > 20:
        h.shield(h._id)
        return

    if turn > 90: 
        h.defend_pos = move_to(op_base_pos, base_pos, 3000)

        if mana > 20:
            #shield spiders targeting OP
            aS = next((s for s in hero_spiders.control if s.threat_for == 2 and s.shield_life == 0), None)
            if aS and len([oh for oh in op_heros.values() if math.dist(oh.position, aS.position) <= 2200]) > 0:
                h.shield(aS._id, "shd AtkS")
                return
            
            #target spider to OP
            aS = next((s for s in hero_spiders.control if not s.threat_for == 2 and s.shield_life == 0), None)
            if aS:
                h.control(aS._id, op_base_pos, "tgt AtkS")
                return


        if math.dist(h.position, h.defend_pos) > 3200:
           h.move( h.defend_pos, "move to AP")
           return
        
        if mana > 20:
            if math.dist(h.position, op_base_pos) < 5000:
                if h.shield_life == 0:
                    h.shield(h._id)
                    return
            
            if len(op_ultra_spiders) > 0:
                uS = next((s for s in op_ultra_spiders if s.shield_life == 0), None)
                if uS:
                    h.shield(uS._id, "shd U-AtkS")
                    return                    
                else:
                    oH = next((oH for oH in op_heros.values() if oH.shield_life == 0 and math.dist(oH.position, op_base_pos) < 6900),None)
                    if oH:
                        if math.dist(oH.position, h.position) <= 2200:
                            h.control(oH._id, base_pos, "ctrl oH")
                            return
                         
            if len(op_critical_spiders) > 0:
                shielded = [s for s in op_critical_spiders if s.shield_life > 0]
                if len(shielded) > 3:
                    oH = next((oH for oH in op_heros.values() if oH.shield_life == 0 and math.dist(oH.position, op_base_pos) < 6900),None)
                    if oH:
                        if math.dist(oH.position, h.position) <= 2200:
                            h.control(oH._id, base_pos, "ctrl oH")
                            return
                        
                if len(op_critical_spiders) > len(shielded):
                    if len( set(hero_spiders.wind).intersection(op_critical_spiders)) > 0:
                        h.wind(op_base_pos)
                        return
                        
                cS = next((s for s in op_critical_spiders if s.shield_life == 0), None)
                if cS:
                    h.shield(cS._id, "shd C-AtkS")
                    return

            if len(hero_spiders.wind) > 0:
                if len([s for s in hero_spiders.wind if s.shield_life == 0 and math.dist(s.position, op_base_pos) <= 7000]) > 0:
                    h.wind(op_base_pos, "push AtkS")
                    return
            
                        
            oH = next((oH for oH in op_heros.values() if oH.shield_life == 0 and math.dist(oH.position, op_base_pos) < 6900), None)
            if oH:
                if math.dist(oH.position, h.position) <= 2200:
                    h.control(oH._id, base_pos)
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

    if (turn > 100 and mana > 20) or mana > 100 :    
        oH = next((oH for oH in sorted(op_heros.values(), key=lambda h: math.dist(base_pos, h.position)) if dangerZone(oH) ), None)
        if oH :
            if h.shield_life == 0:
                h.shield(h._id, "shield <- opH")
                return True               
            
            if oH.shield_life == 0 :
                if math.dist(oH.position, h.position) <= 1200:
                    h.wind(op_base_pos, "push opH")
                    return True
                if math.dist(oH.position, h.position) <= 2200:
                    h.control(oH._id, op_base_pos, "move opH")
                    return True
            
    return False

def safety(h:Hero):
    if len(ultra_spiders) > 0:
        max_dist = 0
        


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


DEFENDER = "D"
SAFETY = "S"
ATTACKER = "A"
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
                heros[_id].was_controlled = True if heros[_id].was_controlled else heros[_id].is_controlled

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

    prevent_success = False
    for h in heros.values():
        
        if role[0] == h._id:
            h.name = DEFENDER
            if turn > 75: h.defend_pos = move_to(base_pos, op_base_pos, 2000)
            if not prevent(h) : defend(h) 
            else: prevent_success = True
        elif role[1] == h._id:
            h.name = SAFETY
            if len([s for s in critical_spiders if s.shield_life != 0]) > 0 or turn > 90:
                h.defend_pos = move_to(base_pos, op_base_pos, 5000)
                if not prevent_success or not prevent(h) : defend(h)
            else:
                attack(h)
            
        else:
            h.name = ATTACKER
            attack(h)

        # Write an action using print
        # To debug: print("Debug messages...", file=sys.stderr, flush=True)

