import sys
import heapq
import time


print(f"DEBUG: Initialization {time.time()}", file=sys.stderr)
# --- A* Pathfinder Class with Debug ---
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
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def find_path(self, start, goal, blocked):
        open_set = []
        heapq.heappush(open_set, (self.heuristic(start, goal), 0, start))
        came_from = {}
        cost_so_far = {start: 0}
        iterations = 0

        while open_set:
            iterations += 1
            if iterations > 1000:
                print("WARNING: A* exceeded 1000 iterations", file=sys.stderr)
                break

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
                new_cost = cost + 1
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (priority, new_cost, neighbor))
                    came_from[neighbor] = current

        print(f"DEBUG: A* failed to find path from {start} to {goal}", file=sys.stderr)
        return [start]


# --- Game Init ---
my_id = int(input())
agent_data_count = int(input())
my_agents_meta = {}
all_agents_meta = {}

for _ in range(agent_data_count):
    agent_id, player, shoot_cd, opt_range, soak_power, splash = map(int, input().split())
    all_agents_meta[agent_id] = {
        "player": player,
        "shoot_cd": shoot_cd,
        "optimal_range": opt_range,
        "soaking_power": soak_power,
        "splash_bombs": splash,
    }
    if player == my_id:
        my_agents_meta[agent_id] = all_agents_meta[agent_id]

width, height = map(int, input().split())
for _ in range(height):
    input()

pathfinder = AStarPathfinder(width, height)


print(f"DEBUG: Initialization Complete. {time.time()}", file=sys.stderr)
turn = 1

# --- Game Loop ---
while True:
    print(f"DEBUG: Turn {turn} Start {time.time()}", file=sys.stderr)

    agent_count = int(input())
    positions = {}
    cooldowns = {}
    wetness = {}
    enemies = []
    my_agents = []

    for _ in range(agent_count):
        agent_id, x, y, cooldown, splash, wet = map(int, input().split())
        positions[agent_id] = (x, y)
        cooldowns[agent_id] = cooldown
        wetness[agent_id] = wet
        if all_agents_meta[agent_id]["player"] != my_id:
            enemies.append(agent_id)
        else:
            my_agents.append(agent_id)

    my_agent_cnt = input()

    target_enemy = max(enemies, key=lambda eid: wetness[eid]) if enemies else None
    target_pos = positions[target_enemy] if target_enemy else None

    print(f"DEBUG: Target enemy {target_enemy} at {target_pos}. {time.time()}" if target_enemy else f"DEBUG: No enemies. {time.time()}", file=sys.stderr)

    planned_positions = set()
    actions = []

    for agent_id in my_agents:
        my_pos = positions[agent_id]
        my_cd = cooldowns[agent_id]
        opt_range = my_agents_meta[agent_id]["optimal_range"]

        print(f"DEBUG: Agent {agent_id} at {my_pos}, cooldown {my_cd}. {time.time()}", file=sys.stderr)

        if target_enemy is not None:
            blocked = set(planned_positions)
            for other_id, pos in positions.items():
                if other_id != agent_id:
                    blocked.add(pos)

            if target_pos in blocked:
                print(f"DEBUG: Target pos {target_pos} in blocked, removing. {time.time()}", file=sys.stderr)
                blocked.remove(target_pos)

            print(f"DEBUG: Finding path for agent {agent_id} to {target_pos}, blocked: {blocked}. {time.time()}", file=sys.stderr)
            path = pathfinder.find_path(my_pos, target_pos, blocked)
            print(f"DEBUG: Path for agent {agent_id}: {path}", file=sys.stderr)

            next_pos = path[1] if len(path) > 1 else my_pos
            planned_positions.add(next_pos)

            future_dist = abs(next_pos[0] - target_pos[0]) + abs(next_pos[1] - target_pos[1])
            can_shoot = my_cd == 0 and future_dist <= 2 * opt_range

            cmds = []
            if can_shoot:
                cmds.append(f"SHOOT {target_enemy}")
                print(f"DEBUG: Agent {agent_id} SHOOT {target_enemy}. {time.time()}", file=sys.stderr)
            elif next_pos != my_pos:
                cmds.append(f"MOVE {next_pos[0]} {next_pos[1]}")
                print(f"DEBUG: Agent {agent_id} MOVE {next_pos[0]} {next_pos[1]}. {time.time()}", file=sys.stderr)
            
            if not cmds:
                cmds = ["HUNKER_DOWN"]
                print(f"DEBUG: Agent {agent_id} HUNKER_DOWN. {time.time()}", file=sys.stderr)

            actions.append(f"{agent_id};{'/'.join(cmds).replace('/', ';')}")
        else:
            actions.append(f"{agent_id};HUNKER_DOWN")
            print(f"DEBUG: Agent {agent_id} HUNKER_DOWN. {time.time()}", file=sys.stderr)

    for act in actions:
        print(act, flush=True)

    print(f"DEBUG: Turn {turn} end. {time.time()}", file=sys.stderr)
    turn += 1
