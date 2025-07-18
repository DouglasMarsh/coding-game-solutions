import sys
import time
import heapq
from dataclasses import dataclass
from typing import List, Tuple, Dict, Set, Optional

@dataclass
class AgentMeta:
    shoot_cd: int
    opt_range: int
    soak_power: int
    splash_bombs: int

@dataclass
class AgentState:
    agent_id: int
    x: int
    y: int
    cooldown: int
    wetness: int

@dataclass
class Tile:
    x: int
    y: int
    tile_type: int  # 0 = empty, 1 = low cover, 2 = high cover

class AStarPathfinder:
    def __init__(self, width, height, grid):
        self.width = width
        self.height = height
        self.grid = grid

    def neighbors(self, node):
        x, y = node
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.grid[ny][nx].tile_type == 0:
                    yield (nx, ny)

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def find_path(self, start, goal, blocked):
        open_set = []
        heapq.heappush(open_set, (self.heuristic(start, goal), 0, start))
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
                new_cost = cost + 1
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (priority, new_cost, neighbor))
                    came_from[neighbor] = current
        return [start]

class GameState:
    def __init__(self, my_id, width, height, grid, agents_meta):
        self.my_id = my_id
        self.width = width
        self.height = height
        self.grid = grid
        self.all_agents_meta = agents_meta
        self.pathfinder = AStarPathfinder(width, height, grid)
        self.my_agents = []
        self.positions = {}
        self.cooldowns = {}
        self.wetness = {}
        self.my_states = {}
        self.enemies = []

    @staticmethod
    def from_input():
        my_id = int(input())
        agent_data_count = int(input())
        agents_meta = {}
        my_agents = []

        for _ in range(agent_data_count):
            agent_id, player, cd, rng, power, bombs = map(int, input().split())
            agents_meta[agent_id] = AgentMeta(cd, rng, power, bombs)
            if player == my_id:
                my_agents.append(agent_id)

        width, height = map(int, input().split())
        grid = [[None] * width for _ in range(height)]
        for y in range(height):
            row = input().split()
            for x in range(width):
                tx, ty, ttype = int(row[x*3]), int(row[x*3+1]), int(row[x*3+2])
                grid[ty][tx] = Tile(tx, ty, ttype)

        state = GameState(my_id, width, height, grid, agents_meta)
        state.my_agents = my_agents
        return state

    def read_turn(self):
        self.positions.clear()
        self.cooldowns.clear()
        self.wetness.clear()
        self.my_states.clear()
        self.enemies.clear()

        agent_count = int(input())
        for _ in range(agent_count):
            agent_id, x, y, cd, splash, wet = map(int, input().split())
            self.positions[agent_id] = (x, y)
            self.cooldowns[agent_id] = cd
            self.wetness[agent_id] = wet
            if agent_id in self.my_agents:
                self.my_states[agent_id] = AgentState(agent_id, x, y, cd, wet)
            else:
                self.enemies.append(agent_id)

class CoverAnalyzer:
    def __init__(self, grid):
        self.grid = grid

    def is_adjacent_to_cover(self, x, y):
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < len(self.grid[0]) and 0 <= ny < len(self.grid):
                if self.grid[ny][nx].tile_type in (1, 2):
                    return True
        return False
    
    def find_best_adjacent_cover_tile( 
        self, x: int, y: int, blocked: Set[Tuple[int, int]], enemy_positions: List[Tuple[int, int]] ) -> Optional[Tuple[int, int]]:
        best = None
        best_score = -1

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < len(self.grid[0]) and 0 <= ny < len(self.grid):
                tile = self.grid[ny][nx]
                if tile.tile_type == 0 and (nx, ny) not in blocked:
                    total_score = 0

                    for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        cx, cy = nx + ddx, ny + ddy
                        if 0 <= cx < len(self.grid[0]) and 0 <= cy < len(self.grid):
                            adj_tile = self.grid[cy][cx]
                            if adj_tile.tile_type in (1, 2):
                                for ex, ey in enemy_positions:
                                    # Vector from cover → candidate
                                    v1x, v1y = nx - cx, ny - cy
                                    # Vector from cover → enemy
                                    v2x, v2y = ex - cx, ey - cy
                                    if (v1x, v1y) == (-v2x, -v2y):
                                        if adj_tile.tile_type == 2:
                                            total_score += 3
                                        elif adj_tile.tile_type == 1:
                                            total_score += 2
                                    else:
                                        if adj_tile.tile_type == 2:
                                            total_score += 1
                                        elif adj_tile.tile_type == 1:
                                            total_score += 0.5

                    if total_score > best_score:
                        best = (nx, ny)
                        best_score = total_score

        return best

class Bot:
    def decide(self, state: GameState, cover: CoverAnalyzer) -> List[str]:
        actions = []
        target_enemy = None
        min_protection = float('inf')
        for eid in state.enemies:
            x, y = state.positions[eid]
            protection = 1 if cover.is_adjacent_to_cover(x, y) else 0
            if protection < min_protection:
                min_protection = protection
                target_enemy = eid

        for aid in state.my_agents:
            state_self = state.my_states[aid]
            meta = state.all_agents_meta[aid]
            target_pos = state.positions.get(target_enemy)

            blocked = set(state.positions.values())
            blocked.discard((state_self.x, state_self.y))

            best_tile = cover.find_best_adjacent_cover_tile(state_self.x, state_self.y, blocked)
            move_tile = best_tile if best_tile else (state_self.x, state_self.y)

            dist = abs(move_tile[0] - target_pos[0]) + abs(move_tile[1] - target_pos[1]) if target_pos else 999
            can_shoot = state_self.cooldown == 0 and target_pos and dist <= 2 * meta.opt_range

            cmds = []
            if move_tile != (state_self.x, state_self.y):
                cmds.append(f"MOVE {move_tile[0]} {move_tile[1]}")
            if can_shoot:
                cmds.append(f"SHOOT {target_enemy}")
            if not cmds:
                cmds = ["HUNKER_DOWN"]

            actions.append(f"{aid};{';'.join(cmds)}")
            print(f"DEBUG: {aid};{';'.join(cmds)}", file=sys.stderr)
            
        return actions

class Game:
    def __init__(self):
        print(f"DEBUG: Initialization {time.time()}", file=sys.stderr)
        self.state = GameState.from_input()
        self.cover = CoverAnalyzer(self.state.grid)

        print(f"DEBUG: GRID {self.state.grid}", file=sys.stderr)

        self.bot = Bot()
        print(f"DEBUG: Initialization Complete {time.time()}", file=sys.stderr)

    def run(self):
        turn = 1
        while True:
            print(f"DEBUG: Turn {turn}. {time.time()}", file=sys.stderr)

            self.state.read_turn()
            actions = self.bot.decide(self.state, self.cover)
            for act in actions:
                print(act, flush=True)
            turn += 1

            print(f"DEBUG: Turn {turn} end. {time.time()}", file=sys.stderr)

Game().run()
