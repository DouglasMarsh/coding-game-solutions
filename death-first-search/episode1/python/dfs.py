import sys
import math


graph = {}
gateways = []

def add_link(n1, n2):
    graph[n1] = graph.get(n1, set())
    graph[n1].add( n2 )

    
    graph[n2] = graph.get(n2, set())
    graph[n2].add( n1 )

def remove_link(n1, n2):
    if n1 in graph:
        graph[n1].remove( n2 )
    if n2 in graph:
        graph[n2].remove( n1 )

def shortest_path(start, end):
    previous = {}
    queue = []

    queue.append( start )
    while queue:
        node = queue.pop()
        for n in graph[ node ]:
            if n in previous:
                continue

            previous[n] = node
            if n == end:
                queue.clear()
                break
            queue.append( n )


    path = []
    current = end
    while current != start:
        path.append( current )
        current = previous[ current ]

    path.append( start )
    path.reverse()

    return path

# n: the total number of nodes in the level, including the gateways
# l: the number of links
# e: the number of exit gateways
n, l, e = [int(i) for i in input().split()]
for i in range(l):
    # n1: N1 and N2 defines a link between these nodes
    n1, n2 = [int(j) for j in input().split()]
    add_link( n1, n2 )

for i in range(e):
    ei = int(input())  # the index of a gateway node
    gateways.append( ei )

# game loop
while True:
    si = int(input())  # The index of the node on which the Bobnet agent is positioned this turn
    paths = []
    for g in gateways:
        paths.append( shortest_path(g, si) )
    
    paths.sort( key = lambda p: len( p ))
    shortest = paths[0]

    print(f"{shortest[0]} {shortest[1]}")

    # Write an action using print
    # To debug: print("Debug messages...", file=sys.stderr, flush=True)
