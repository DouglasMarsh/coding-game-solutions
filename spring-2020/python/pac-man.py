import sys
import math
import random

from typing import  NamedTuple, Union

################################# AStar #######################################
from abc import ABC, abstractmethod
from typing import Callable, Dict, Iterable, TypeVar, Generic
from dataclasses import dataclass, astuple
from math import inf as infinity
import operator


# introduce generic type
T = TypeVar("T")
U = TypeVar("U")

@dataclass
class Path(Generic[T]):

     # this stores the data like a tuple, but isn't required
     __slots__ = ("points", "cost")

     points: list[T]
     cost: float

     # if you want to be able to unpack like a tuple...
     def __iter__(self):
          yield from astuple(self)

class SearchNode(Generic[T]):
    """Representation of a search node"""

    __slots__ = ("data", "gscore", "fscore", "closed", "came_from", "in_openset")

    def __init__(
        self, data: T, gscore: float = infinity, fscore: float = infinity
    ) -> None:
        self.data = data
        self.gscore = gscore
        self.fscore = fscore
        self.closed = False
        self.in_openset = False
        self.came_from: Union[None, SearchNode[T]] = None

    def __lt__(self, b: "SearchNode[T]") -> bool:
        """Natural order is based on the fscore value & is used by heapq operations"""
        return self.fscore < b.fscore
    

class SearchNodeDict(Dict[T, SearchNode[T]]):
    """A dict that returns a new SearchNode when a key is missing"""

    def __missing__(self, k) -> SearchNode[T]:
        v = SearchNode(k)
        self.__setitem__(k, v)
        return v

SearchNodeType = TypeVar("SearchNodeType", bound=SearchNode)

class OpenSet(Generic[SearchNodeType]):
    def __init__(self) -> None:
        self.sortedlist:list[SearchNodeType] = []
        self.keyfunc = operator.attrgetter("fscore")

    def push(self, item: SearchNodeType) -> None:
        item.in_openset = True
        self.sortedlist.append(item)
        self.sortedlist.sort(key=self.keyfunc)

    def pop(self) -> SearchNodeType:
        item = self.sortedlist.pop(0)
        item.in_openset = False
        return item

    def remove(self, item: SearchNodeType) -> None:
        self.sortedlist.remove(item)
        self.sortedlist.sort(key=self.keyfunc)
        item.in_openset = False

    def __len__(self) -> int:
        return len(self.sortedlist)

class AStar(ABC, Generic[T]):
    __slots__ = ()

    @abstractmethod
    def heuristic_cost_estimate(self, current: T, goal: T) -> float:
        """
        Computes the estimated (rough) distance between a node and the goal.
        The second parameter is always the goal.
        This method must be implemented in a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def distance_between(self, n1: T, n2: T) -> float:
        """
        Gives the real distance between two adjacent nodes n1 and n2 (i.e n2
        belongs to the list of n1's neighbors).
        n2 is guaranteed to belong to the list returned by the call to neighbors(n1).
        This method must be implemented in a subclass.
        """

    @abstractmethod
    def neighbors(self, node: T) -> Iterable[T]:
        """
        For a given node, returns (or yields) the list of its neighbors.
        This method must be implemented in a subclass.
        """
        raise NotImplementedError

    def _neighbors(self, current: SearchNode[T], search_nodes: SearchNodeDict[T]) -> Iterable[SearchNode]:
        return (search_nodes[n] for n in self.neighbors(current.data))

    def is_goal_reached(self, current: T, goal: T) -> bool:
        """
        Returns true when we can consider that 'current' is the goal.
        The default implementation simply compares `current == goal`, but this
        method can be overwritten in a subclass to provide more refined checks.
        """
        return current == goal

    def reconstruct_path(self, last: SearchNode[T], reversePath=False) -> Path[T]:
        def _gen():
            cost = 0
            points: list[T] = []
            current = last
            while current:
                cost += current.gscore
                points.append(current.data)
                current = current.came_from

            return Path(points, cost)

        path = _gen()

        if reversePath:
            return path
        else:
            return Path(list(reversed(path.points)), path.cost)

    def astar(
        self, start: T, goal: T, reversePath: bool = False
    ) -> Union[None, Path[T]]:
        if self.is_goal_reached(start, goal):
            return Path([start],0)

        openSet: OpenSet[SearchNode[T]] = OpenSet()
        searchNodes: SearchNodeDict[T] = SearchNodeDict()
        startNode = searchNodes[start] = SearchNode(
            start, gscore=0.0, fscore=self.heuristic_cost_estimate(start, goal)
        )
        openSet.push(startNode)

        while openSet:
            current = openSet.pop()

            if self.is_goal_reached(current.data, goal):
                return self.reconstruct_path(current, reversePath)

            current.closed = True

            for neighbor in self._neighbors(current, searchNodes):
                if neighbor.closed:
                    continue

                tentative_gscore = current.gscore + self.distance_between(
                    current.data, neighbor.data
                )

                if tentative_gscore >= neighbor.gscore:
                    continue

                neighbor_from_openset = neighbor.in_openset

                if neighbor_from_openset:
                    # we have to remove the item from the heap, as its score has changed
                    openSet.remove(neighbor)

                # update the node
                neighbor.came_from = current
                neighbor.gscore = tentative_gscore
                neighbor.fscore = tentative_gscore + self.heuristic_cost_estimate(
                    neighbor.data, goal
                )

                openSet.push(neighbor)

        return None


def find_path(
    start: U,
    goal: U,
    neighbors_fnct: Callable[[U], Iterable[U]],
    reversePath=False,
    heuristic_cost_estimate_fnct: Callable[[U, U], float] = lambda a, b: infinity,
    distance_between_fnct: Callable[[U, U], float] = lambda a, b: 1.0,
    is_goal_reached_fnct: Callable[[U, U], bool] = lambda a, b: a == b,
) -> Union[Path[U], None]:
    """A non-class version of the path finding algorithm"""

    class FindPath(AStar):
        def heuristic_cost_estimate(self, current: U, goal: U) -> float:
            return heuristic_cost_estimate_fnct(current, goal)  # type: ignore

        def distance_between(self, n1: U, n2: U) -> float:
            return distance_between_fnct(n1, n2)

        def neighbors(self, node) -> Iterable[U]:
            return neighbors_fnct(node)  # type: ignore

        def is_goal_reached(self, current: U, goal: U) -> bool:
            return is_goal_reached_fnct(current, goal)

    return FindPath().astar(start, goal, reversePath)

#End AStar

Point = NamedTuple("Point", [('x', int), ('y', int)])

# Grab the pellets as fast as you can!
class Pellet:
    def __init__(self, pos: Point, value: int) -> None:
        self.pos = pos
        self.value = value

    def __repr__(self) -> str:
        return f"Pellet at {self.pos} with value {self.value}"

    def __hash__(self) -> int:
        return hash( self.__repr__())
    
class PacMan:
    pos:Point

    path: Union[list[Point], None] = None
    target:Union[None, Point,Pellet,"PacMan"] = None

    type = ""
    boost = 0
    cooldown = 0
    def __init__(self, _id: int) -> None:
        self._id = _id

    def target_pos(self) -> Union[None,Point]:
        if not self.target: 
            return None
        elif isinstance(self.target,Point):
            return self.target
        else:
            return self.target.pos

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

    def __repr__(self) -> str:
        return f"PacMan({self._id}) at {self.pos}"


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
def heuristic_cost_estimate( p1: Point, p2: Point ) -> float:
    return math.dist(p1,p2)

def cost_between(p1: Point, p2: Point) -> float:
    pm = next((pm for pm in pac_men if pm.pos == p1), None)
    if pm :
        return cost_to(pm, p2)                
                
    else:
        p = pellets.get(p2, None)
        if p:
            return -p.value
    
    if grid[p2] == "p" or grid[p2] == "?": return -1
        
    return 1

def cost_to(pm: PacMan, p: Point) -> float:
    
    op = next((op for op in op_pac_men if op.pos == p), None)
    if op:
        return op_cost(pm, op)
    
    collide = next((mp for mp in pac_men if mp.pos == p), None)
    if collide:
        return 2000
    
    cost = 0
    pe = pellets.get(p, None)
    if pe : cost -= pe.value
    else: cost += 1

    return cost
def op_cost(pm:PacMan, op:PacMan, dist_to = 1) -> float:
    if op:
        # i can eat them, -100
        if WINS[pm.type] == op.type:
            return -100/dist_to
        # i can change they cant, -50
        if pm.cooldown == 0 and op.cooldown > 0:
            return -50/dist_to
        
        # they can eat me, 1000
        if pm.cooldown > 0 and (WINS[op.type] == pm.type or op.cooldown == 0):
            return 10000
        
        # if same type, and neither can change, avoid 500
        if pm.type == op.type and pm.cooldown > 0 and op.cooldown > 0:
            return  500/dist_to
        
        # if both can change, avoid 250
        if pm.cooldown == 0 and op.cooldown == 0:
            return 250/dist_to
    
    return 0
def print_path(start: Point, end: Point, path: list[Point]):
    for y in range(height):
        row = ""
        for x in range(width):
            p = Point(x,y)
            if p == start:
                row += "S"
            elif p == end:
                row += "E"
            elif p in path:
                row += "*"
            elif grid[p] == "#":
                row += "#"
            else: row += ' '
        
        print(row, file=sys.stderr, flush=True)

def path_to_target(pm: PacMan, t: Point) -> Path[Point]:
    path = find_path(pm.pos, t, reversePath=True,
                neighbors_fnct=find_neighbors,
                heuristic_cost_estimate_fnct=heuristic_cost_estimate,
                distance_between_fnct=cost_between)
    if path:
        return path

    raise Exception(f"No path between {pm} and {t}")
    
def set_targets( pac_men: list[PacMan]):

    big_pellet_list = list(big_pellets)
    pellet_list = list(pellets.values())
    possible_pellets = [ p for p in grid if grid[p] == 'p' ]
    unknown_points = [ p for p in grid if grid[p] == '?' ]
    empty_points =  [ p for p in grid if grid[p] == ' ' ]

    # set targets    
    for pm in pac_men:

        if pm.target:
            if isinstance(pm.target, PacMan) and pm.target in op_pac_men:
                continue
            elif isinstance(pm.target, Pellet) and \
                (pm.target in pellet_list or pm.target.pos in possible_pellets) :
                continue
            elif isinstance(pm.target, Point) and pm.target in unknown_points:
                continue
            else:
                pm.target = None
                pm.path = None

        if big_pellet_list:
            path = next( iter(sorted( [ (p, path_to_target(pm, p.pos)) for p in big_pellet_list ], key=lambda p: p[1].cost)), None)
            if path:
                pm.target = path[0]
                pm.path = path[1].points
                big_pellet_list.remove( pm.target )
                continue

        if pellet_list:
            visible_points = pm.visible_points()
            path = next( iter(sorted( [ (p, path_to_target(pm, p.pos)) for p in pellet_list if p.pos in visible_points ], key=lambda p: p[1].cost)), None)
            if not path:
                p = random.choice( pellet_list )
                path = (p, path_to_target(pm, p.pos))            
            
            pm.target = path[0]
            pm.path = path[1].points
            pellet_list.remove( pm.target )
            continue

        if possible_pellets:
            p = random.choice( possible_pellets )
            path = (p, path_to_target(pm, p))            
        
            pm.target = path[0]
            pm.path = path[1].points
            possible_pellets.remove( pm.target )
            continue

        if unknown_points:
            p = random.choice( unknown_points )
            path = (p, path_to_target(pm, p))            
        
            pm.target = path[0]
            pm.path = path[1].points
            unknown_points.remove( pm.target )
            continue

        
        p = random.choice( empty_points )
        path = (p, path_to_target(pm, p))           
    
        pm.target = path[0]
        pm.path = path[1].points
        empty_points.remove( pm.target )

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

grid: dict[Point, str] = {}
open_points: list[Point] = []

# width: size of the grid
# height: top left corner is (x=0, y=0)
width, height = [int(i) for i in input().split()]
for y in range(height):
    row = input()  # one line of the grid: space " " is floor, pound "#" is wall
    out = ""
    for x in range(width):
        grid[Point(x,y)] = row[x]
        if row[x] == " ":
           grid[Point(x,y)] = "?"
           open_points.append( Point(x,y))
        
        out += grid[Point(x,y)]
    print(row, file=sys.stderr, flush=True)

all_pac_men: dict[(int, int), PacMan] = {}

# game loop
while True:
    pac_men: list[PacMan] = []
    op_pac_men: list[PacMan] = []

    pellets: dict[Point, Pellet ] = {}
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
        mine = int( inputs[1] )
        pm = all_pac_men.setdefault((pac_id,mine) , PacMan( pac_id ))
        pm.pos = Point(int(inputs[2]), int(inputs[3]))
        pm.type = inputs[4]
        pm.boost = int(inputs[5])
        pm.cooldown = int(inputs[6])
        grid[pm.pos] = " "

        if inputs[1] != "0":
            pac_men.append( pm )
        else:
            op_pac_men.append( pm )
    
    visible_pellet_count = int(input())  # all pellets in sight
    for i in range(visible_pellet_count):
        # value: amount of points this pellet is worth
        x, y, value = [int(j) for j in input().split()]
        p = Pellet( Point(x,y), value )
        pellets[p.pos] = p

        grid[p.pos] = 'p'
        if p.value == 10:
            big_pellets.append( p )

    set_targets( pac_men )
    for pm in pac_men:
        if pm.path:
            print(f"{pm} targeting {pm.target}", file=sys.stderr, flush=True)
            print_path(pm.pos, pm.target_pos(), pm.path )
        
    output:list[str] = []
    for pm in pac_men:
                
        neighbors = set(find_neighbors(pm.pos))
        for n in list(neighbors):
            neighbors.update( find_neighbors(n) )   
        
        near_op_pacmen = [op for op in op_pac_men if op.pos in neighbors]
        if near_op_pacmen:
            op = near_op_pacmen[0]
            if pm.cooldown == 0:
                pm.target = op                
                pm.path = path_to_target(pm, op.pos).points
                
                print(f"{pm} targeting {pm.target}", file=sys.stderr, flush=True)
                print_path(pm.pos, pm.target_pos(), pm.path )

                # switch to winning type if necessary
                if not WINS[pm.type] == op.type:
                    output.append(f"SWITCH {pm._id} {LOSES[op.type]}")
                    continue
                else:
                    output.append(f"SPEED {pm._id}")
                    continue
                     
            elif op.cooldown > 0 and WINS[pm.type] == op.type:
                pm.target = op
                pm.path = path_to_target(pm, op.pos).points

                print(f"{pm} targeting {pm.target}", file=sys.stderr, flush=True)
                print_path(pm.pos, pm.target_pos(), pm.path )

        
        if pm.path:
            pt = pm.path.pop()
            self_collision = next(iter([mp for mp in pac_men if mp.pos == pt ]), None)
            if self_collision:
                if pm.pos not in self_collision.path:
                    pt = pm.pos
                elif len( pm.path) > len(self_collision.path):
                    # move along collision path until we can get off it
                    neighbors = find_neighbors( pm.pos )
                    not_on_path = set(self_collision.path) - set( neighbors )
                    if not_on_path:
                        pt = not_on_path[0]
                    else:
                        pt = self_collision.path[-2]

            output.append(f"MOVE {pm._id} {pt.x} {pt.y}")
            continue

    print(" | ".join( output))

    # Write an action using print
    # To debug: print("Debug messages...", file=sys.stderr, flush=True)

    # MOVE <pacId> <x> <y>
    #print("MOVE 0 15 10")
