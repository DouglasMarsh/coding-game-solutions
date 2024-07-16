import sys
import math
import random

from collections import namedtuple
from typing import Callable
  
Point = namedtuple("Point", "x y")

# Grab the pellets as fast as you can!
class reversor:
    def __init__(self, obj):
        self.obj = obj

    def __eq__(self, other):
        return other.obj == self.obj

    def __lt__(self, other):
        return other.obj < self.obj

class Pellet:
    def __init__(self, pos: Point, value: int) -> None:
        self.pos = pos
        self.value = value

class PacMan:
    pos:Point
    target:Pellet = None

    type = ""
    boost = 0
    cooldown = 0
    def __init__(self, _id: int) -> None:
        self._id = _id

# width: size of the grid
# height: top left corner is (x=0, y=0)
width, height = [int(i) for i in input().split()]
for i in range(height):
    row = input()  # one line of the grid: space " " is floor, pound "#" is wall

pac_men: dict[int, PacMan] = {}
op_pac_men: dict[int, PacMan] = {}

# game loop
while True:
    pellets: list[ Pellet ] = [] 
    big_pellets: list[ Pellet ] = []
    my_score, opponent_score = [int(i) for i in input().split()]
    visible_pac_count = int(input())  # all your pacs and enemy pacs in sight
    for i in range(visible_pac_count):
        inputs = input().split()
        # 0: pac number (unique within a team)
        # 1: true if this pac is yours
        # 2-3: position in the grid
        # unused in wood leagues
        # unused in wood leagues
        # unused in wood leagues

        pac_id = int(inputs[0])  # pac number (unique within a team)
        mine = inputs[1] != "0"
        if mine:
            pm = pac_men.setdefault(pac_id, PacMan( pac_id ))            
            pm.pos = Point(int(inputs[2]), int(inputs[3]))
            pm.type = inputs[4]
            pm.boost = int(inputs[5])
            pm.cooldown = int(inputs[6])
        else:
            pm = op_pac_men.setdefault(pac_id, PacMan( pac_id ))            
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
    
    output:list[str] = []
    for pm in pac_men.values():

        #handle collisions
        if pm.pos in [op.pos for op in op_pac_men]:
            pm.target = random.choice( pellets )

        p = pm.target
        
        if p and p in pellets:
            print(f"MOVE to pellet at {p.pos.x} {p.pos.y} with value {p.value} at dist { math.dist(p.pos, pm.pos) }", file=sys.stderr, flush=True)
            output.append( f"MOVE {pm._id} {p.pos.x} {p.pos.y}" )
            pellets.remove( p )
            if p in big_pellets: big_pellets.remove( p )
            continue

        if len( big_pellets) > 0:
            
            big_pellets.sort(key = lambda p: math.dist(p.pos, pm.pos), reverse=True)
            p = big_pellets.pop()
            pellets.remove( p )
            pm.target = p

            print(f"MOVE to pellet at {p.pos.x} {p.pos.y} with value {p.value} at dist { math.dist(p.pos, pm.pos) }", file=sys.stderr, flush=True)
            output.append( f"MOVE {pm._id} {p.pos.x} {p.pos.y}" )
            continue
        
        pellets.sort(key = lambda p: math.dist(p.pos, pm.pos), reverse=True)
        p = pellets.pop()
        pm.target = p
        
        print(f"MOVE to pellet at {p.pos.x} {p.pos.y} with value {p.value} at dist { math.dist(p.pos, pm.pos) }", file=sys.stderr, flush=True)
        output.append(f"MOVE {pm._id} {p.pos.x} {p.pos.y}")
        
    print(" | ".join( output))

    # Write an action using print
    # To debug: print("Debug messages...", file=sys.stderr, flush=True)

    # MOVE <pacId> <x> <y>
    #print("MOVE 0 15 10")
