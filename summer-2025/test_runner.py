
import sys
import subprocess
from copy import deepcopy
from collections import defaultdict
import math

class Agent:
    def __init__(self, agent_id, player, shoot_cd, opt_range, power, bombs):
        self.id = agent_id
        self.player = player
        self.shoot_cooldown = shoot_cd
        self.optimal_range = opt_range
        self.soaking_power = power
        self.splash_bombs = bombs
        self.x = -1
        self.y = -1
        self.cooldown = 0
        self.wetness = 0
        self.is_alive = True
        self.action = None
        self.message = ""

class GameState:
    def __init__(self, width, height, tiles, agents):
        self.width = width
        self.height = height
        self.tiles = tiles  # (x, y) -> tile_type
        self.agents = agents  # id -> Agent
        self.turn = 0
        self.score = {0: 0, 1: 0}

    def clone(self):
        return deepcopy(self)

    def get_alive_agents(self, player):
        return [a for a in self.agents.values() if a.player == player and a.is_alive]

def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def load_scenario(path):
    with open(path) as f:
        lines = f.read().strip().split('
')

    i = 0
    my_id = int(lines[i]); i += 1
    agent_count = int(lines[i]); i += 1

    agents = {}
    for _ in range(agent_count):
        parts = lines[i].split(); i += 1
        agent = Agent(int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5]))
        agents[agent.id] = agent

    width, height = map(int, lines[i].split()); i += 1
    tiles = {}
    for _ in range(width * height):
        x, y, tile_type = map(int, lines[i].split()); i += 1
        tiles[(x, y)] = tile_type

    return my_id, GameState(width, height, tiles, agents)

def run_bot(bot_path, input_lines):
    proc = subprocess.Popen(['python', bot_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate('
'.join(input_lines) + '
')
    return stdout.strip().split('
')

def apply_move(agent, move_command):
    parts = move_command.split()
    if len(parts) != 3:
        return
    try:
        _, x_str, y_str = parts
        tx, ty = int(x_str), int(y_str)
    except ValueError:
        return

    # BFS to find shortest path around cover
    from collections import deque
    visited = set()
    queue = deque()
    queue.append((agent.x, agent.y, []))

    while queue:
        cx, cy, path = queue.popleft()
        if (cx, cy) in visited:
            continue
        visited.add((cx, cy))

        if (cx, cy) == (tx, ty):
            if len(path) >= 1:
                next_x, next_y = path[0]
                agent.next_move = (next_x, next_y)
            return

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in agent.__class__.tiles:
                tile_type = agent.__class__.tiles[(nx, ny)]
                if tile_type == 0 and (nx, ny) not in [(a.x, a.y) for a in agent.__class__.agents.values() if a.is_alive]:
                    queue.append((nx, ny, path + [(nx, ny)]))

    # No path or blocked
    agent.next_move = None

def apply_hunker(agent):
    agent.action = "HUNKER_DOWN"

def apply_message(agent, text):
    agent.message = text

def apply_throw(attacker, tx, ty, state):
    if attacker.splash_bombs <= 0:
        return
    if manhattan((attacker.x, attacker.y), (tx, ty)) > 4:
        return
    affected = [(tx + dx, ty + dy) for dx in [-1, 0, 1] for dy in [-1, 0, 1]]
    for (ax, ay) in affected:
        for agent in state.agents.values():
            if agent.x == ax and agent.y == ay and agent.is_alive:
                agent.wetness += 30
    attacker.splash_bombs -= 1

def apply_shoot(attacker, target, state):
    if not target.is_alive:
        return
    dist = manhattan((attacker.x, attacker.y), (target.x, target.y))
    if dist > attacker.optimal_range * 2:
        return  # Out of range

    dmg = attacker.soaking_power
    if dist > attacker.optimal_range:
        dmg //= 2

    dx = target.x - attacker.x
    dy = target.y - attacker.y

    cover_bonus = 0
    if abs(dx) + abs(dy) > 1:
        for dir in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            cx, cy = target.x + dir[0], target.y + dir[1]
            if (cx, cy) in state.tiles:
                tile_type = state.tiles[(cx, cy)]
                if tile_type > 0:
                    sx, sy = target.x - dir[0], target.y - dir[1]
                    if (attacker.x, attacker.y) == (sx, sy):
                        cover_bonus = max(cover_bonus, tile_type)

    if cover_bonus == 1:
        dmg = dmg * 50 // 100
    elif cover_bonus == 2:
        dmg = dmg * 25 // 100

    if target.action == "HUNKER_DOWN":
        if cover_bonus == 1:
            dmg = dmg * 50 // 100
        elif cover_bonus == 2:
            dmg = dmg * 100 // 100
        else:
            dmg = dmg * 75 // 100

    target.wetness += dmg

def simulate_turn(state, bot1_path, bot2_path):
    if state.score[0] - state.score[1] >= 600 or not state.get_alive_agents(1):
        print("Player 0 wins by dominance or elimination.")
        sys.exit(0)
    elif state.score[1] - state.score[0] >= 600 or not state.get_alive_agents(0):
        print("Player 1 wins by dominance or elimination.")
        sys.exit(0)
    elif state.turn >= 100:
        if state.score[0] > state.score[1]:
            print("Player 0 wins on points after 100 turns.")
        elif state.score[1] > state.score[0]:
            print("Player 1 wins on points after 100 turns.")
        else:
            print("Draw after 100 turns.")
        sys.exit(0)
    # Decrease cooldown for all agents
    for agent in state.agents.values():
        if agent.cooldown > 0:
            agent.cooldown -= 1
    print(f"Simulating turn {state.turn}...")
    agent_by_player = {0: [], 1: []}
    for a in state.agents.values():
        if a.is_alive:
            agent_by_player[a.player].append(a)

    input1 = [str(len(state.agents))]
    input2 = [str(len(state.agents))]
    for a in state.agents.values():
        input_line = f"{a.id} {a.x} {a.y} {a.cooldown} {a.splash_bombs} {a.wetness}"
        input1.append(input_line)
        input2.append(input_line)

    input1.append(str(len(agent_by_player[0])))
    input2.append(str(len(agent_by_player[1])))

    output1 = run_bot(bot1_path, input1)
    output2 = run_bot(bot2_path, input2)

    for a in state.agents.values():
        a.action = None
        a.message = ""

    parsed_ids = set()
    for bot_output, player in [(output1, 0), (output2, 1)]:
        for line in bot_output:
            parts = line.strip().split(';')
            if not parts:
                continue
            agent_id = int(parts[0]) if parts[0].strip().isdigit() else None
            actions = [p.strip() for p in parts if p.strip() and not p.strip().isdigit()]

            if agent_id is None or agent_id not in state.agents:
                print(f"Invalid agent id in output: {line}")
                sys.exit(1)

            agent = state.agents[agent_id]
            if agent.player != player or not agent.is_alive:
                print(f"Agent {agent_id} is not controlled by player {player} or is dead.")
                sys.exit(1)

            parsed_ids.add(agent_id)
            agent.action = actions

    for a in state.agents.values():
        if a.is_alive and a.id not in parsed_ids:
            print(f"Agent {a.id} missing action.")
            sys.exit(1)

    # Process MOVE
    for agent in state.agents.values():
        if agent.is_alive and isinstance(agent.action, list):
            for act in agent.action:
                if act.startswith("MOVE"):
                    apply_move(agent, act)

    # Process HUNKER_DOWN
    for agent in state.agents.values():
        if agent.is_alive and isinstance(agent.action, list):
            for act in agent.action:
                if act == "HUNKER_DOWN":
                    apply_hunker(agent)

    # Process SHOOT, THROW, MESSAGE
    for agent in state.agents.values():
        if agent.is_alive and isinstance(agent.action, list):
            for act in agent.action:
                if act.startswith("SHOOT"):
                    _, target_id = act.split()
                    if agent.cooldown > 0:
                        continue  # can't shoot yet
                    if int(target_id) in state.agents:
                        apply_shoot(agent, state.agents[int(target_id)], state)
                        agent.cooldown = agent.shoot_cooldown
                elif act.startswith("THROW"):
                    _, x, y = act.split()
                    apply_throw(agent, int(x), int(y), state)
                elif act.startswith("MESSAGE"):
                    _, *msg = act.split()
                    apply_message(agent, ' '.join(msg))

    for agent in state.agents.values():
        if agent.wetness >= 100:
            agent.is_alive = False

    # Resolve MOVE collisions
    destination_map = defaultdict(list)
    for agent in state.agents.values():
        if agent.is_alive and hasattr(agent, 'next_move') and agent.next_move:
            destination_map[agent.next_move].append(agent)

    for dest, movers in destination_map.items():
        if len(movers) == 1:
            movers[0].x, movers[0].y = dest  # valid move
        # else: conflict, cancel all

    for agent in state.agents.values():
        if hasattr(agent, 'next_move'):
            del agent.next_move

    # Calculate tile control for scoring
    from collections import deque
    control_map = {}
    for x in range(state.width):
        for y in range(state.height):
            if (x, y) not in state.tiles:
                continue  # skip out-of-bounds

            best_dist = {0: float('inf'), 1: float('inf')}
            for agent in state.agents.values():
                if not agent.is_alive:
                    continue
                dist = manhattan((x, y), (agent.x, agent.y))
                if agent.wetness >= 50:
                    dist *= 2  # wet agents are less influential
                best_dist[agent.player] = min(best_dist[agent.player], dist)

            if best_dist[0] < best_dist[1]:
                control_map[(x, y)] = 0
            elif best_dist[1] < best_dist[0]:
                control_map[(x, y)] = 1

    owned_tiles = defaultdict(int)
    for owner in control_map.values():
        owned_tiles[owner] += 1

    diff = owned_tiles[0] - owned_tiles[1]
    if diff > 0:
        state.score[0] += diff
    elif diff < 0:
        state.score[1] += -diff

    state.turn += 1
