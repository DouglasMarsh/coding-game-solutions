import sys
import math
import random

from typing import NamedTuple, Union

Point = NamedTuple("Point", [('x', int), ('y', int)])

# Grab the pellets as fast as you can!
class Pellet:
    def __init__(self, pos: Point, value: int) -> None:
        self.pos = pos
        self.value = value
    def __repr__(self) -> str:
        return f"Pellet{self.pos}:{self.value}"
    def __hash__(self) -> int:
        return hash( self.__repr__())
    
class PacMan:
    pos:Point

    target:Union[None,Point] = None    
    point_target:Union[None,Point] = None

    type = ""
    boost = 0
    cooldown = 0
    def __init__(self, _id: int) -> None:
        self._id = _id

def set_targets( pac_men: list[PacMan]):
    global pellets
    global big_pellets

    # set targets    
    if big_pellets or pellets:
        targets: dict[Pellet, list[PacMan]] = {}
        for pm in pac_men:
            if not pm.target or pm.target not in pellets:
                pm.target = None
                if big_pellets:    
                    pm.target = next((p for p in sorted(big_pellets, key=lambda p: math.dist(p.pos, pm.pos))), None)
                elif pellets:    
                    pm.target = next((p for p in sorted(pellets, key=lambda p: math.dist(p.pos, pm.pos))), None)

            if pm.target:
                targets.setdefault( pm.target, []).append( pm )

        re_target: list[PacMan] = []
        for t in targets:
            pellets.remove( t )
            if t in big_pellets:
                big_pellets.remove( t )
            
            if len( targets[t]) > 1:
                targets[t].sort(key=lambda pm: math.dist(pm.pos, t.pos ))
                re_target += targets[t][1:]

        if re_target:
            set_targets( re_target )
    else:
        for pm in pac_men:
            pm.target = None

grid: dict[Point, str] = {}
open_points: list[Point] = []

# width: size of the grid
# height: top left corner is (x=0, y=0)
width, height = [int(i) for i in input().split()]
for y in range(height):
    row = input()  # one line of the grid: space " " is floor, pound "#" is wall
    for x in range(width):
        grid[Point(x,y)] = row[x]
        if row[x] == " ":
            open_points.append( Point(x,y))


all_pac_men: dict[int, PacMan] = {}

# game loop
while True:
    pac_men: list[PacMan] = []
    op_pac_men: list[PacMan] = []

    pellets: list[ Pellet ] = [] 
    big_pellets: list[ Pellet ] = []

    my_score, opponent_score = [int(i) for i in input().split()]
    visible_pac_count = int(input())  # all your pacs and enemy pacs in sight
    for i in range(visible_pac_count):
        inputs = input().split()
        # 0: pac number (unique within a team)
        # 1: true if this pac is yours
        # 2-3: position in the grid
        # type: ROCK or PAPER or SCISSORS OR DEAD
        # boost remaining: number of turns of boost (0-5)
        # cooldown turns left (number of turns before Pac can boost or switch form)

        pac_id = int(inputs[0])  # pac number (unique within a team)
        pm = all_pac_men.setdefault(pac_id, PacMan( pac_id ))
        mine = inputs[1] != "0"
        if mine:
            pac_men.append( pm )
            pm.pos = Point(int(inputs[2]), int(inputs[3]))
            pm.type = inputs[4]
            pm.boost = int(inputs[5])
            pm.cooldown = int(inputs[6])
        else:
            op_pac_men.append( pm )          
            pm.pos = Point(int(inputs[2]), int(inputs[3]))
            pm.type = inputs[4]
            pm.boost = int(inputs[5])
            pm.cooldown = int(inputs[6])
    
    visible_pellet_count = int(input())  # all pellets in sight
    for i in range(visible_pellet_count):
        # value: amount of points this pellet is worth
        x, y, value = [int(j) for j in input().split()]
        p = Pellet( Point(x,y), value )
        pellets.append( p )
        if p.value == 10:
            big_pellets.append( p )
    

    set_targets( pac_men )
    
    output:list[str] = []
    for pm in pac_men:

        if len([cp for cp in all_pac_men.values() if cp._id != pm._id and cp.pos == pm.pos]) > 0:
            pt = random.choice( open_points )
            print(f"Collision!! MOVE to random point at {pt.x} {pt.y}", file=sys.stderr, flush=True)
            output.append(f"MOVE {pm._id} {pt.x} {pt.y}")
            continue
        
        op = next((op for op in op_pac_men if math.dist(pm.pos, op.pos) == (2 if op.boost > 0 else 1) ), None)
        if op and pm.cooldown == 0:
            if op.type == "ROCK" and pm.type != "PAPER":
                output.append(f"SWITCH {pm._id} PAPER")
                continue
            elif op.type == "PAPER" and pm.type != "SCISSORS":
                output.append(f"SWITCH {pm._id} SCISSORS")
                continue
            elif op.type == "SCISSORS" and pm.type != "ROCK":
                output.append(f"SWITCH {pm._id} ROCK")
                continue
        
        op = next((op for op in op_pac_men if math.dist(pm.pos, op.pos) < 5+op.boost), None)
        if not op and pm.cooldown == 0 and pm.boost == 0:
            output.append(f"SPEED {pm._id}")
            continue
        
        if pm.target:
            p = pm.target 
            pm.point_target = None
            print(f"MOVE to pellet at {p.pos.x} {p.pos.y} with value {p.value} at dist { math.dist(p.pos, pm.pos) }", file=sys.stderr, flush=True)
            output.append(f"MOVE {pm._id} {p.pos.x} {p.pos.y}")
            continue
        
        if not pm.point_target:            
            pm.point_target = random.choice( open_points )

        pt = pm.point_target
        print(f"MOVE to random point at {pt.x} {pt.y}", file=sys.stderr, flush=True)
        output.append(f"MOVE {pm._id} {pt.x} {pt.y}")
        continue


    print(" | ".join( output))

    # Write an action using print
    # To debug: print("Debug messages...", file=sys.stderr, flush=True)

    # MOVE <pacId> <x> <y>
    #print("MOVE 0 15 10")
