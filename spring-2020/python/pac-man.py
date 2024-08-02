import sys
import math
import random

from typing import NamedTuple, Union, Iterable


ROCK = "ROCK"
PAPER = "PAPER"
SCISSORS = "SCISSORS"
WINS = {
    ROCK: SCISSORS,
    PAPER: ROCK,
    SCISSORS: PAPER
}
LOSES = {
    ROCK: PAPER,
    PAPER: SCISSORS,
    SCISSORS: ROCK
}


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
    type = ""
    boost = 0
    cooldown = 0
    
    target:Point = None
    section:tuple[int,int]
    turn_complete = False

    def __init__(self, _id: int) -> None:
        self._id = _id

    def __str__(self) -> str:
        return f"PacMan({self._id}) @ {self.pos}"

    def visible_points(self) -> Iterable[Point]:
        
        #forward
        x = self.pos.x
        y = self.pos.y
        while x < width and grid[Point(x,y)] != "#":
            yield Point(x,y)
            x += 1
        #reverse
        x = self.pos.x
        y = self.pos.y
        while x >= 0 and grid[Point(x,y)] != "#":
            yield Point(x,y)
            x -= 1
        #up
        x = self.pos.x
        y = self.pos.y
        while y >= 0 and grid[Point(x,y)] != "#":
            yield Point(x,y)
            y -= 1
        #down
        x = self.pos.x
        y = self.pos.y
        while y < height and grid[Point(x,y)] != "#":
            yield Point(x,y)
            y += 1

def section_grid(cnt: int) -> list[tuple[int,int]]:
    s_width = int(width / cnt)
    s_start = 0
    s_end = s_width
    sections = []
    for s in range( cnt ):
        sections.append((s_start, s_end))
        s_start = s_end
        s_end += s_width
    
    sections[-1] = (sections[-1][0], width)
    return sections

def dist_from_section(section: tuple[int,int], p: Point) -> float:
    center = int((section[1] - section[0])/2)
    return abs( center - p.x)
    
def in_section(section: tuple[int,int], p: Point) -> bool:
    return p.x >= section[0] and p.x <= section[1]

def need_target() -> Iterable[PacMan]:
    for pm in pac_men.values():
        if not pm.target:
            print(f"{pm} has no target", file=sys.stderr, flush=True)
            yield pm
        elif big_pellets and [p for p in big_pellets if p.pos == pm.target]:
            # big pellets target, no nothing
            continue
        else:
            confirmed_section = [ p for p in confirmed_pellets if in_section(pm.section, p) ]
            if confirmed_section and pm.target not in confirmed_section:
                print(f"{pm} has target {p} that is not confirmed. Retargeting", file=sys.stderr, flush=True)
                pm.target = None
                yield pm
                continue

            possible_section =  [ p for p in possible_pellets if in_section(pm.section, p) ]
            if possible_section and pm.target not in possible_section:
                print(f"{pm} has possible target {p} that is not not valid. Retargeting", file=sys.stderr, flush=True)
                pm.target = None
                yield pm
                continue

def set_targets(pac_men: Iterable[PacMan] ):
    
    b_pellets: set[Pellet] = set(big_pellets)
    c_pellets: set[Pellet] = set(confirmed_pellets.values() )
    p_pellets: set[Pellet] = set(possible_pellets.values() )

    for pm in pac_men:
        bsp = sorted([ p for p in b_pellets if in_section(pm.section, p.pos) ], key= lambda p: math.dist(pm.pos, p.pos))
        csp = sorted([ p for p in c_pellets if in_section(pm.section, p.pos) ], key= lambda p: math.dist(pm.pos, p.pos))
        psp = sorted([ p for p in p_pellets if in_section(pm.section, p.pos) ], key= lambda p: math.dist(pm.pos, p.pos))
        
        if bsp:
            p = bsp[0]
            b_pellets.remove( p )
        elif csp:
            p = csp[0]
            c_pellets.remove( p )
        elif psp:
            p = psp[0]
            p_pellets.remove( p )
        else:
            p = random.choice( list(possible_pellets.values() ))

        pm.target = p.pos
        
        print(f"{pm} targeting {p}", file=sys.stderr, flush=True)

def find_neighbors(p: Point) -> list[Point]:
    neighbors: list[Point] = []
    pLeft = Point(width-1,p.y) if p.x == 0 else Point(p.x-1, p.y)
    pRight = Point(0,p.y) if p.x+1 == width else Point(p.x+1, p.y)
    pUp = Point(p.x, height-1) if p.y == 0 else Point(p.x, p.y - 1)
    pDown = Point(p.x, 0) if p.y + 1 == height else Point(p.x, p.y + 1)

    if grid.get(pLeft, None) != '#': neighbors.append( pLeft )
    if grid.get(pRight, None) != '#': neighbors.append( pRight )
    if grid.get(pUp, None) != '#': neighbors.append( pUp )
    if grid.get(pDown, None) != '#': neighbors.append( pDown )

    return neighbors


grid: dict[Point, str] = {}
possible_pellets: dict[Point, Pellet] = {}
confirmed_pellets: dict[Point, Pellet] = {}

# width: size of the grid
# height: top left corner is (x=0, y=0)
width, height = [int(i) for i in input().split()]
for y in range(height):
    row = input()  # one line of the grid: space " " is floor, pound "#" is wall
    for x in range(width):
        p = Point(x,y) 
        grid[p] = row[x]
        if row[x] == " ":
            possible_pellets[p] = Pellet(p, 1)

pac_men: dict[int, PacMan] = {}
pac_men_cnt = 0
turn = 0
# game loop
while True:
    turn += 1

    op_pac_men: dict[int, PacMan] = {}
    big_pellets: list[ Pellet ] = []

    my_score, opponent_score = [int(i) for i in input().split()]
    visible_pac_count = int(input())  # all your pacs and enemy pacs in sight

    alive_pm: list[int] = []

    for i in range(visible_pac_count):
        inputs = input().split()
        # 0: pac number (unique within a team)
        # 1: true if this pac is yours
        # 2-3: position in the grid
        # type: ROCK or PAPER or SCISSORS OR DEAD
        # boost remaining: number of turns of boost (0-5)
        # cooldown turns left (number of turns before Pac can boost or switch form)

        pac_id = int(inputs[0])  # pac number (unique within a team)
        mine = inputs[1] != "0"
        if mine:            
            pm = pac_men.setdefault(pac_id, PacMan( pac_id ) )
            alive_pm.append( pac_id )
        else:
            pm = op_pac_men.setdefault(pac_id, PacMan( pac_id ) )

        pm.pos = Point(int(inputs[2]), int(inputs[3]))
        pm.type = inputs[4]
        pm.boost = int(inputs[5])
        pm.cooldown = int(inputs[6])
        pm.turn_complete = False
        
        if pm.pos in possible_pellets:
            del possible_pellets[ pm.pos ]
        if pm.pos in confirmed_pellets:
            del confirmed_pellets[ pm.pos ]

    pac_men = {k: pac_men[k] for k in pac_men if k in alive_pm}

    if turn == 1 or len(pac_men) != pac_men_cnt:
        pac_men_cnt = len(pac_men)
        sections = section_grid( pac_men_cnt )

        pm_set = set( pac_men.values() )
        for s in sections:
            sorted_pm = sorted(pm_set, key=lambda pm: dist_from_section(s, pm.pos))
            pm = next( (pm for pm in sorted_pm if in_section(s, pm.pos)), None)
            if not pm:
                pm = sorted_pm[0]
            
            pm.section = s
            pm_set.remove( pm )
            print(f"{pm} assigned to section {pm.section}", file=sys.stderr, flush=True)

    visible_pellet_count = int(input())  # all pellets in sight
    visible_pellets: set[Point] = set()
    for i in range(visible_pellet_count):
        # value: amount of points this pellet is worth
        x, y, value = [int(j) for j in input().split()]
        p = Pellet( Point(x,y), value )
        visible_pellets.add( p.pos )
        if p.value == 10:
            big_pellets.append( p )
        
        confirmed_pellets[p.pos] = p
        if p.pos in possible_pellets:
            del possible_pellets[ p.pos ]
    
    
    # remove pellets that have been eaten
    for pm in pac_men.values():
        for pos in pm.visible_points():
            if pos not in visible_pellets:
                if pos in possible_pellets:
                    del possible_pellets[ pos ]
                if pos in confirmed_pellets:
                    del confirmed_pellets[ pos ]

    set_targets( need_target() )
    
    output:list[str] = []
    for pm in pac_men.values():
        pm.turn_complete = True

        neighbors = set(find_neighbors(pm.pos))
        for n in list(neighbors):
            neighbors.update( find_neighbors(n) )   
        
        if op_pac_men:
            near_op_pacmen = [op for op in sorted(op_pac_men.values(), key=lambda op: math.dist(op.pos, pm.pos)) if op.pos in neighbors]
            if near_op_pacmen:
                op = near_op_pacmen[0]

                if pm.cooldown == 0:

                    if op.cooldown == 0:
                        # assume op will switch to beat my current type, so I switch to 
                        output.append(f"SWITCH {pm._id} {LOSES[LOSES[pm.type]]}")
                        print(f"{pm} attacking {op} switch to {LOSES[LOSES[pm.type]]}", file=sys.stderr, flush=True)
                        continue
                    else:
                        # switch to winning type if necessary
                        if not WINS[pm.type] == op.type:                 
                            output.append(f"SWITCH {pm._id} {LOSES[op.type]}")
                            print(f"{pm} attacking {op} switch to {LOSES[op.type]}", file=sys.stderr, flush=True)
                            continue
                        else:
                            if pm.boost == 0:                                
                                output.append(f"SPEED {pm._id}")
                                print(f"{pm} attacking {op} speed", file=sys.stderr, flush=True)
                                continue
                            else:
                                output.append(f"MOVE {pm._id} {op.pos.x} {op.pos.y}")
                                print(f"{pm} attacking {op} move to {op.pos}", file=sys.stderr, flush=True)
                                continue
                elif op.cooldown != 0 and WINS[pm.type] == op.type:
                    output.append(f"MOVE {pm._id} {op.pos.x} {op.pos.y}")
                    print(f"{pm} attacking {op} move to {op.pos}", file=sys.stderr, flush=True)
                    continue
                    
                else:
                    # I can't change, op can, run away
                    n = next( iter( sorted(neighbors, key=lambda n: math.dist(op.pos, n), reverse=True)))
                    output.append(f"MOVE {pm._id} {n.x} {n.y}")
                    print(f"{pm} running from {op} to {n}", file=sys.stderr, flush=True)
                    continue


        neighbor_pm = set([npm.pos for npm in pac_men.values() if npm._id != pm._id and npm.pos in neighbors])
        if neighbor_pm:
            p = random.choice( [p for p in neighbors if p not in neighbor_pm] )
            output.append(f"MOVE {pm._id} {p.x} {p.y}")
            print(f"{pm} avoiding neighboring pm", file=sys.stderr, flush=True)
            continue


        p = pm.target
        output.append(f"MOVE {pm._id} {p.x} {p.y}")
        print(f"{pm} move to target {p}", file=sys.stderr, flush=True)
        continue


    print(" | ".join( output))

    # Write an action using print
    # To debug: print("Debug messages...", file=sys.stderr, flush=True)

    # MOVE <pacId> <x> <y>
    #print("MOVE 0 15 10")