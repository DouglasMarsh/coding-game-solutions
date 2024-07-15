import sys
import math

from collections import namedtuple
from typing import Callable
  
Point = namedtuple("Point", "x y")

# Grab the pellets as fast as you can!

class PacMan:
    type = ""
    boost = 0
    cooldown = 0
    def __init__(self, _id: int) -> None:
        self._id = _id
        

class Pellet:
    def __init__(self, pos: Point, value: int) -> None:
        self.pos = pos
        self.value = value

# width: size of the grid
# height: top left corner is (x=0, y=0)
width, height = [int(i) for i in input().split()]
for i in range(height):
    row = input()  # one line of the grid: space " " is floor, pound "#" is wall

pac_men: dict[int, PacMan] = {}
op_pac_men: dict[int, PacMan] = {}
pellets: list[ Pellet ] = [] 
big_pellets: list[ Pellet ] = []

# game loop
while True:
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
        pellets.append( Pellet( Point(x,y), value ))

    pellets.sort( lambda p: p.value) 

    for pm in pac_men.values():
        p = pellets.pop()
        print(f"MOVE {pm._id} {p.pos.x} {p.pos.x}")


    # Write an action using print
    # To debug: print("Debug messages...", file=sys.stderr, flush=True)

    # MOVE <pacId> <x> <y>
    #print("MOVE 0 15 10")
