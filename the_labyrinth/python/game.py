import sys
import math
import heapq


def heuristic(node, goal):
    x1, y1 = node
    x2, y2 = goal

    return abs(x1 - x2) + abs(y1 - y2)

def astar(maze: dict, start, goal, ignore = None):

    c_cost = {cell: float('inf') for cell in maze }
    c_cost[start] = 0

    h_cost = {cell: float('inf') for cell in maze }
    h_cost[start] = heuristic(start, goal)

    open_list = []

    heapq.heappush(open_list, (h_cost[start], h_cost[start], start))
    
    a_path = {}
    while open_list:
        _, _, current_node = heapq.heappop(open_list)

        if current_node == goal:
            break

        neighbors = get_neighbors(maze, current_node, ignore)
        for n in neighbors:
            tc_cost = c_cost[ current_node ] + 1
            th_cost = tc_cost + heuristic( n, goal )

            if tc_cost < c_cost[ n ]:
                c_cost[n] = tc_cost
                h_cost[n] = th_cost
                heapq.heappush(open_list, (th_cost, heuristic( n, goal ),  n))
                a_path[n] = current_node

    if a_path.get(goal):
        path = {}
        cell = goal
        while cell != start:
            path[ a_path[cell]] = cell
            cell = a_path[ cell ]

        return path
    
    return None

def get_neighbors(maze:dict, node, ignore):
    x, y = node
    neighbors = []

    # Add adjacent nodes (up, down, left, right)
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        new_x, new_y = x + dx, y + dy
        neighbor = (new_x, new_y)
        if maze.get(neighbor):
            if maze[ neighbor ] == '#':
                #print(f"Node: {neighbor} is a wall", file=sys.stderr, flush=True)
                pass
            elif ignore and ignore == neighbor:
                #print(f"Node: {neighbor} is explicitly ignored", file=sys.stderr, flush=True)
                pass
            else:
                neighbors.append(neighbor)
        
            

    return neighbors

def verify_path(maze: dict, path: dict):
    for step in path:
        node = path[step]
        if maze[ node ] == '?':
            return False
    return True
    

def direction_to_node(start, target):
    x1, y1 = start
    x2, y2 = target

    if x1 == x2 and y2 > y1: return 'RIGHT'
    if x1 == x2 and y2 < y1: return 'LEFT'
    if x1 > x2 and y2 == y1: return 'UP'
    if x1 < x2 and y2 == y1: return 'DOWN'

# r: number of rows.
# c: number of columns.
# a: number of rounds between the time the alarm countdown is activated and the time the alarm goes off.
r, c, a = [int(i) for i in input().split()]

escaping = False
start_pos = None
cr = None

# game loop
while True:
    # kr: row where Kirk is located.
    # kc: column where Kirk is located.
    kr, kc = [int(i) for i in input().split()]
    kirk = (kr,kc)
    
    maze = {}
    unknown_list = []
    for x in range(r):
        row = input()  # C of the characters in '#.TC?' (i.e. one line of the ASCII maze).
        print(row, file=sys.stderr, flush=True)      
          
        for y, n in enumerate( row ):
            node = (x,y)
            maze[ node ] = n

            if n == '?':                
                heapq.heappush(unknown_list, (heuristic( kirk, node ),  node))
            elif n == 'T':
                start_pos = node
            elif n == 'C':
                cr = node
    
    if kirk == cr:
        escaping = True

    # if we know where the control room is find a path between it and the start
    if cr:        
        print(f"Control Room at { cr }", file=sys.stderr, flush=True)
        escape_path = astar(maze, cr, start_pos)

        # if we are already escaping, move to next node
        if escaping:            
            next = escape_path[ kirk ]
            print(f"Escaping. Moving to { next }", file=sys.stderr, flush=True)
            print(direction_to_node(kirk , next) )
            continue
        
        # not escaping but we have verified path between cr and start
        if len(escape_path) <= a and verify_path(maze, escape_path):
            
            print(f"Verified Escape Path. Finding path to control room", file=sys.stderr, flush=True)

            # find path between current position and cr
            # if verified, follow it
            cr_path = astar(maze, kirk, cr)
            if verify_path(maze, cr_path):
                next = cr_path[ kirk ]
                print(f"Verified Control Room Path. Moving to Node { next }", file=sys.stderr, flush=True)
                print(direction_to_node(kirk , next) )
                continue
    
    # if we are here, we either dont know where the control room is
    # or we can't build verified paths to/from control room
    # so we explore. astar will return None for a node that
    # it can't find a path to
    while True:
        _, unknown_node = heapq.heappop(unknown_list)
        explore_path = astar(maze, kirk, unknown_node, cr)
        if explore_path: break

    next = explore_path[ kirk ]
    
    print(f"Exploring. Target { unknown_node}. Moving to {next}", file=sys.stderr, flush=True)
    print(direction_to_node(kirk , next) )

    
    # Write an action using print
    # To debug: print("Debug messages...", file=sys.stderr, flush=True)

