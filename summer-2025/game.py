import sys
import heapq

# --- A* Pathfinder Class ---
class AStarPathfinder:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def neighbors(self, node):
        x, y = node
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield (nx, ny)

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])  # Manhattan

    def find_path(self, start, goal, blocked):
        open_set = []
        heapq.heappush(open_set, (0 + self.heuristic(start, goal), 0, start))
        came_from = {}
        cost_so_far = {start: 0}

        while open_set:
            _, cost, current = heapq.heappop(open_set)

            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path

            for neighbor in self.neighbors(current):
                if neighbor in blocked:
                    continue
                new_cost = cost_so_far[current] + 1
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (priority, new_cost, neighbor))
                    came_from[neighbor] = current

        return [start]  # No path found

# --- Initial Setup ---
my_id = int(input())
agent_data_count = int(input())
agent_ids = []

for _ in range(agent_data_count):
    agent_id, player, *_ = map(int, input().split())
    if player == my_id:
        agent_ids.append(agent_id)

width, height = map(int, input().split())
for _ in range(height):
    input()  # Skip terrain

# Targets for League 1
TARGETS = [(6, 1), (6, 3)]

pathfinder = AStarPathfinder(width, height)

# --- Game Loop ---
while True:
    agent_count = int(input())
    agent_states = {}
    for _ in range(agent_count):
        agent_id, x, y, *_ = map(int, input().split())
        agent_states[agent_id] = (x, y)

    my_agent_count = int(input())
    planned_positions = set()
    commands = []

    for i in range(my_agent_count):
        agent_id = agent_ids[i]
        curr_pos = agent_states[agent_id]
        target = TARGETS[i]

        if i == 0:
            # Bot 1: greedy logic
            x, y = curr_pos
            tx, ty = target
            if x < tx:
                x += 1
            elif x > tx:
                x -= 1
            elif y < ty:
                y += 1
            elif y > ty:
                y -= 1
            next_pos = (x, y)
        else:
            # Bot 2: A* pathfinding that avoids Bot 1's planned tile
            blocked = set(planned_positions)
            blocked.update(pos for aid, pos in agent_states.items() if aid != agent_id)
            path = pathfinder.find_path(curr_pos, target, blocked)
            next_pos = path[1] if len(path) > 1 else curr_pos

        planned_positions.add(next_pos)
        commands.append(f"{agent_id}; MOVE {next_pos[0]} {next_pos[1]}")

    for cmd in commands:
        print(cmd)
