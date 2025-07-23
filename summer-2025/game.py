import math
import random
import sys
import heapq
from dataclasses import dataclass
from typing import List, Dict, NamedTuple, Optional, Set, Tuple, Union
from collections import deque
import time

class Timer:
    def __init__(self, label):
        self.label = label
        self.start = None

    def __enter__(self):
        self.start = time.perf_counter()

    def __exit__(self, *args):
        elapsed = (time.perf_counter() - self.start) * 1000
        print(f"[TIMER] {self.label}: {elapsed:.2f}ms", file=sys.stderr)

# --- Type Aliases ---
class Position(NamedTuple):
    x: int
    y: int

    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def distance_to(self, other: 'Position') -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)

@dataclass
class Tile:
    position: Position
    tile_type: int  # 0 = empty, 1 = low cover, 2 = high cover

@dataclass
class AgentMeta:
    my_id:int
    agent_id: int
    is_enemy: bool
    shoot_cd: int
    opt_range: int
    soak_power: int
    splash_bombs: int

@dataclass
class Agent:
    metadata: AgentMeta
    position: Position
    cooldown: int
    bomb_cnt: int
    wetness: int
    is_hunkered = False

    @property
    def agent_id(self) -> int:
        return self.metadata.agent_id

    @property
    def is_enemy(self) -> bool:
        return self.metadata.is_enemy

    @property
    def is_friendly(self) -> bool:
        return not self.is_enemy

    def has_bombs(self) -> bool:
        return self.bomb_cnt > 0
    
    def same_team(self, a:'Agent'):
        return self.metadata.my_id == a.metadata.my_id
    
    def clone(self):
        return Agent(self.metadata, self.position, self.cooldown, self.bomb_cnt, self.wetness)

Grid = List[List[Tile]]

class AStarPathfinder:
    def __init__(self, width: int, height: int, static_blocked: Set[Position]):
        self.width = width
        self.height = height
        self.static_blocked = static_blocked

    def neighbors(self, node: Position, blocked: Set[Position]) -> List[Position]:
        x, y = node
        results = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                neighbor = Position(nx, ny)
                if neighbor not in blocked:
                    results.append(neighbor)
        return results

    def heuristic(self, a: Position, b: Position) -> int:
        return abs(a.x - b.x) + abs(a.y - b.y)

    def find_path(self, start: Position, goal: Position, dynamic_blocked: Set[Position]) -> List[Position]:
        blocked = self.static_blocked | dynamic_blocked

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

            for neighbor in self.neighbors(current, blocked):
                new_cost = cost + 1
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (priority, new_cost, neighbor))
                    came_from[neighbor] = current

        return [start]

class CoverAnalyzer:
    def __init__(self, grid: Grid):
        self.grid = grid

    def is_adjacent_to_cover(self, pos: Position) -> bool:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = pos.x + dx, pos.y + dy
            if 0 <= nx < len(self.grid[0]) and 0 <= ny < len(self.grid):
                if self.grid[ny][nx].tile_type in (1, 2):
                    return True
        return False

class GameState:
    """GameState object"""
    def __init__(self, my_id: int, width: int, height: int, grid: List[List[Tile]], blocked: Set[Position], agents_meta: Dict[int, AgentMeta]):
        self.my_id = my_id
        self.width = width
        self.height = height
        self.grid = grid
        self.blocked = blocked
        self.all_agents_meta = agents_meta
        self.pathfinder = AStarPathfinder(width, height, blocked)
        self.my_agents: List[Agent] = []
        self.enemies: List[Agent] = []
        self.my_score = 0
        self.enemy_score = 0
        self.my_dist_map: List[List[int]] = []
        self.enemy_dist_map: List[List[int]] = []

    @staticmethod
    def from_input():
        my_id = int(input())
        agent_data_count = int(input())
        agents_meta: Dict[int, AgentMeta] = {}

        for _ in range(agent_data_count):
            agent_id, player, cd, rng, power, bombs = map(int, input().split())
            agents_meta[agent_id] = AgentMeta(my_id, agent_id, player != my_id, cd, rng, power, bombs)

        width, height = map(int, input().split())
        grid: List[List[Optional[Tile]]] = [[None for _ in range(width)] for _ in range(height)]
        blocked: Set[Position] = set()

        for _ in range(height):
            row = input().split()
            for x in range(width):
                tx, ty, ttype = int(row[x*3]), int(row[x*3+1]), int(row[x*3+2])
                grid[ty][tx] = Tile(Position(tx, ty), ttype)
                if ttype != 0:
                    blocked.add(Position(tx, ty))

        state = GameState(my_id, width, height, grid, blocked, agents_meta)

        return state
    
    def compute_distance_maps(self) -> Tuple[List[List[int]], List[List[int]]]:
        width, height = self.width, self.height

        def bfs(agents: List[Agent]) -> List[List[int]]:
            visited = [[-1 for _ in range(width)] for _ in range(height)]
            queue = deque()
            for agent in agents:
                weight = 2 if agent.wetness >= 50 else 1
                queue.append((agent.position.x, agent.position.y, 0, weight))
                visited[agent.position.y][agent.position.x] = 0
            while queue:
                x, y, dist, weight = queue.popleft()
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        new_dist = dist + weight
                        if visited[ny][nx] == -1 or visited[ny][nx] > new_dist:
                            visited[ny][nx] = new_dist
                            queue.append((nx, ny, new_dist, weight))
            return visited

        return bfs(self.my_agents), bfs(self.enemies)

    def compute_scores(self):
        my_dist, enemy_dist = self.compute_distance_maps()
        my_tiles = 0
        enemy_tiles = 0

        for y in range(self.height):
            for x in range(self.width):
                md = my_dist[y][x]
                ed = enemy_dist[y][x]
                if md == -1 and ed != -1:
                    enemy_tiles += 1
                elif ed == -1 and md != -1:
                    my_tiles += 1
                elif md != -1 and ed != -1:
                    if md < ed:
                        my_tiles += 1
                    elif ed < md:
                        enemy_tiles += 1

                delta = my_tiles - enemy_tiles
        turn_my_score = delta if delta > 0 else 0
        turn_enemy_score = -delta if delta < 0 else 0

        self.my_score += turn_my_score
        self.enemy_score += turn_enemy_score

        # Cache distance maps for external use
        self.my_dist_map = my_dist
        self.enemy_dist_map = enemy_dist

    def read_turn(self):
        self.my_agents.clear()
        self.enemies.clear()

        agent_count = int(input())
        for _ in range(agent_count):
            agent_id, x, y, cd, bombs, wet = map(int, input().split())
            agent = Agent(self.all_agents_meta[agent_id], Position(x, y), cd, bombs, wet)
            if agent.metadata.is_enemy:
                self.enemies.append(agent)
            else:
                self.my_agents.append(agent)

        # Read my_agent_cnt but ignore it
        input()

        self.compute_scores()

    def debug_string(self) -> str:
        lines = []
        lines.append("[GRID]")
        for y in range(self.height):
            row_str = f"{y}: "
            for x in range(self.width):
                pos = Position(x, y)
                tile = self.grid[y][x]
                char = "."
                if tile.tile_type == 1:
                    char = "L"
                elif tile.tile_type == 2:
                    char = "H"
                for agent in self.my_agents:
                    if agent.position == pos:
                        char = str(agent.agent_id)
                for enemy in self.enemies:
                    if enemy.position == pos:
                        char = "E"
                row_str += f"{char} "
            lines.append(row_str.strip())

        lines.append("\n[AGENTS]")
        for a in self.my_agents:
            lines.append(f"{a.agent_id} @ ({a.position.x},{a.position.y}) cd={a.cooldown} b={a.bomb_cnt} w={a.wetness}")
        for e in self.enemies:
            lines.append(f"E{e.agent_id} @ ({e.position.x},{e.position.y}) w={e.wetness}")
        return "\n".join(lines)

class TacticalBot:
    def __init__(self, state: GameState):  # Added danger map caching
        self.state = state
        self.grid = state.grid
        self.pathfinder = state.pathfinder
        self.cover = CoverAnalyzer(self.grid)
        self.tile_control = self.compute_tile_control()
        self.danger_map = self.compute_danger_map()

    def compute_score_delta(self) -> int:
        my_tiles = sum(1 for row in self.tile_control for v in row if v == 1)
        enemy_tiles = sum(1 for row in self.tile_control for v in row if v == -1)
        return my_tiles - enemy_tiles

    def get_strategy_mode(self) -> str:
        delta = self.compute_score_delta()
        early_game = self.state.my_score + self.state.enemy_score < 10
        if early_game:
            return "aggressive"
        if delta < -30:
            return "aggressive"
        elif delta > 100:
            return "defensive"
        return "balanced"

    def compute_tile_control(self) -> List[List[int]]:
        width, height = self.state.width, self.state.height
        control_map = [[0 for _ in range(width)] for _ in range(height)]

        my_dist = self.state.my_dist_map
        enemy_dist = self.state.enemy_dist_map

        for y in range(height):
            for x in range(width):
                md = my_dist[y][x]
                ed = enemy_dist[y][x]
                if md == -1 and ed != -1:
                    control_map[y][x] = -1
                elif ed == -1 and md != -1:
                    control_map[y][x] = 1
                elif md != -1 and ed != -1:
                    if md < ed:
                        control_map[y][x] = 1
                    elif ed < md:
                        control_map[y][x] = -1
                    else:
                        control_map[y][x] = 0
        return control_map

    def compute_danger_map(self) -> Dict[Position, float]:
        danger_map = {}
        for y in range(self.state.height):
            for x in range(self.state.width):
                pos = Position(x, y)
                incoming_damage = 0

                for enemy in self.state.enemies:
                    if enemy.cooldown > 0:
                        continue

                    dist = pos.distance_to(enemy.position)
                    if dist > 2 * enemy.metadata.opt_range:
                        continue

                    range_mult = 1.0 if dist <= enemy.metadata.opt_range else 0.5
                    dx = pos.x - enemy.position.x
                    dy = pos.y - enemy.position.y
                    step_x = 0 if dx == 0 else dx // abs(dx)
                    step_y = 0 if dy == 0 else dy // abs(dy)

                    between_x = pos.x - step_x
                    between_y = pos.y - step_y

                    cover_mult = 1.0
                    if 0 <= between_x < self.state.width and 0 <= between_y < self.state.height:
                        cover_tile = self.grid[between_y][between_x]
                        if cover_tile.tile_type == 2:
                            cover_mult = 0.25
                        elif cover_tile.tile_type == 1:
                            cover_mult = 0.5

                    damage = int(enemy.metadata.soak_power * range_mult * cover_mult)
                    incoming_damage += damage

                # Convert cumulative damage to "danger" based on time-to-death
                if incoming_damage == 0:
                    danger = 0.0
                else:
                    turns_to_die = 100.0 / incoming_damage
                    danger = 1.0 / turns_to_die  # danger = 0.25 if agent dies in 4 turns

                danger_map[pos] = danger

        return danger_map

    def find_best_move_tile(self, agent: Agent, turn: int, max_depth: int = 6) -> Optional[Position]:
        
        visited = set()
        frontier = [(agent.position, 0)]
        best_tile = None
        best_score = float('inf')
        strategy = self.get_strategy_mode()

        if strategy == "aggressive":
            danger_weight = 10.0
            control_weight = -25.0
        elif strategy == "defensive":
            danger_weight = 80.0
            control_weight = -4.0
        else:
            danger_weight = 30.0
            control_weight = -10.0

        def advance_bias(pos: Position) -> float:
            return (self.state.width - pos.x) * 0.2

        def evaluate_tile_danger(tile: Position) -> float:
            return self.danger_map.get(tile, 0.0)

        while frontier:
            current, depth = frontier.pop(0)
            if depth > max_depth or current in visited:
                continue
            visited.add(current)

            tile = self.grid[current.y][current.x]
            if tile.tile_type != 0:
                continue

            danger = evaluate_tile_danger(current)
            control_score = -self.tile_control[current.y][current.x]
            bias = advance_bias(current)

            score = danger_weight * danger + control_weight * control_score - bias

            if danger == 0 and control_score == 0:
                score -= 5.0  # encourage forward movement when all else is equal

            if score < best_score:
                best_score = score
                best_tile = current

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = current.x + dx, current.y + dy
                if 0 <= nx < self.state.width and 0 <= ny < self.state.height:
                    neighbor = Position(nx, ny)
                    if neighbor not in visited:
                        frontier.append((neighbor, depth + 1))

        return best_tile

    def decide(self, turn: int) -> List[str]:
        with Timer("decide"):
            actions = []
            blocked = set(a.position for a in self.state.my_agents + self.state.enemies)

            for agent in self.state.my_agents:
                with Timer(f"decide for Agent {agent.agent_id}"):
                    cmds = []
                    moved = False
                    attacked = False

                    best_tile = self.find_best_move_tile(agent, turn)
                    move_step = None
                    if best_tile and best_tile != agent.position:
                        path = self.state.pathfinder.find_path(agent.position, best_tile, blocked)
                        if len(path) > 1:
                            move_step = path[1]
                            cmds.append(f"MOVE {move_step.x} {move_step.y}")
                            blocked.add(move_step)
                            moved = True
                    
                    
                    if agent.cooldown == 0:
                        potential_pos = move_step if move_step else agent.position
                        best_target = None
                        best_damage = -1
                        for enemy in self.state.enemies:
                            dist = potential_pos.distance_to(enemy.position)
                            if dist <= 2 * agent.metadata.opt_range:
                                range_mult = 1.0 if dist <= agent.metadata.opt_range else 0.5
                                damage = int(agent.metadata.soak_power * range_mult)
                                threat_score = damage + (100 - enemy.wetness)
                                if threat_score > best_damage:
                                    best_damage = threat_score
                                    best_target = enemy.agent_id
                        if best_target is not None:
                            if best_damage >= 10 or self.get_strategy_mode() == "aggressive":
                                cmds.append(f"SHOOT {best_target}")
                            attacked = True

                    if not attacked and agent.has_bombs():
                        best_tile = None
                        max_hits = 0
                        friendlies = {a.position for a in self.state.my_agents}
                        origin = move_step if move_step else agent.position

                        for dx in range(-4, 5):
                            for dy in range(-4, 5):
                                if abs(dx) + abs(dy) > 4:
                                    continue
                                tx, ty = origin.x + dx, origin.y + dy
                                if not (0 <= tx < self.state.width and 0 <= ty < self.state.height):
                                    continue
                                center = Position(tx, ty)
                                aoe = [
                                    Position(tx + ox, ty + oy)
                                    for ox in [-1, 0, 1]
                                    for oy in [-1, 0, 1]
                                    if 0 <= tx + ox < self.state.width and 0 <= ty + oy < self.state.height
                                ]
                                if any(p in friendlies for p in aoe):
                                    continue
                                hits = sum(1 for e in self.state.enemies if e.position in aoe)
                                if hits > max_hits:
                                    max_hits = hits
                                    best_tile = center

                        if best_tile and max_hits >= 2:
                            cmds.append(f"THROW {best_tile.x} {best_tile.y}")
                            attacked = True

                if not attacked and not moved:
                    print("no movement or attack. computing fallback", file=sys.stderr)

                    if self.state.my_score < 300 or self.state.enemy_score < 300:
                        cmds.append(f"MOVE {int(self.state.width/2)} {agent.position.y}")
                    else:
                        cmds.append("HUNKER_DOWN")

                cmds.append(f"MESSAGE {self.get_strategy_mode().capitalize()}")
                print(f"{agent}  → Strategy: {self.get_strategy_mode()}", file=sys.stderr)
                actions.append(f"{agent.agent_id};{';'.join(cmds)}")

            return actions

class MCTS:
    @dataclass
    class MoveAction:
        target: Position
        def __str__(self):
            return f"MOVE {self.target.x} {self.target.y}"
    @dataclass
    class ShootAction:
        target_id: int
        def __str__(self):
            return "SHOOT {self.target_id}"
    @dataclass
    class ThrowAction:
        target_pos: Position
        def __str__(self):
            return f"THROW {self.target_pos.x} {self.target_pos.y}"

    @dataclass
    class HunkerAction:
        def __str__(self):
            return "HUNKER_DOWN"

    Action = Union['MCTS.MoveAction','MCTS.ShootAction', 'MCTS.ThrowAction', 'MCTS.HunkerAction']
    CombatAction = Union['MCTS.ShootAction', 'MCTS.ThrowAction', 'MCTS.HunkerAction']

    class MiniGameState:
        """Trim version of GameState to support MCTS"""
        def __init__(self, width: int, height: int, grid: Grid, my_score: int, enemy_score: int,
                    pathfinder: AStarPathfinder, agents: List[Agent], enemies: List[Agent]):
            self.width = width
            self.height = height
            self.grid = grid
            self.pathfinder = pathfinder
            self.agents = agents
            self.enemies = enemies
            self.all_agents = agents + enemies
            self.my_score = my_score
            self.enemy_score = enemy_score

        @staticmethod
        def from_game_state(state: GameState) -> 'MCTS.MiniGameState':
            return MCTS.MiniGameState(
                width=state.width,
                height=state.height,
                grid=state.grid,
                my_score=state.my_score,
                enemy_score=state.enemy_score,
                pathfinder=state.pathfinder,
                agents=[a.clone() for a in state.my_agents],
                enemies=[e.clone() for e in state.enemies]
            )

        def clone(self) -> 'MCTS.MiniGameState':
            return MCTS.MiniGameState(
                self.width,
                self.height,
                self.grid,
                self.my_score,
                self.enemy_score,
                self.pathfinder,
                [a.clone() for a in self.agents],
                [e.clone() for e in self.enemies]
            )

        def apply_action(self, agent_id: int, action: Optional['MCTS.Action']):
            if not action:
                return

            agent = next((a for a in self.all_agents if a.agent_id == agent_id), None)
            if not agent or agent.wetness >= 100:
                return  # dead agent, skip

            if action:
                if isinstance(action, MCTS.MoveAction) and action.target != agent.position:
                    if all(action.target != other.position for other in self.all_agents):
                        agent.position = action.target

                if isinstance(action, MCTS.ShootAction):
                    if agent.cooldown > 0:
                        return
                    target = next((e for e in self.all_agents if e.agent_id == action.target_id and e.wetness < 100), None)
                    if target:
                        dist = agent.position.distance_to(target.position)
                        if dist <= 2 * agent.metadata.opt_range:
                            dmg = agent.metadata.soak_power * (1.0 if dist <= agent.metadata.opt_range else 0.5)
                            target.wetness += int(dmg)
                            agent.cooldown = agent.metadata.shoot_cd

                elif isinstance(action, MCTS.ThrowAction):
                    if agent.bomb_cnt > 0:
                        tx, ty = action.target_pos.x, action.target_pos.y
                        for e in self.all_agents:
                            if abs(e.position.x - tx) <= 1 and abs(e.position.y - ty) <= 1:
                                e.wetness += 30
                        agent.bomb_cnt -= 1

                elif isinstance(action, MCTS.HunkerAction):
                    agent.is_hunkered = True

        def simulate_turn(self, actions: List[Tuple[int,Optional['MCTS.MoveAction'],Optional['MCTS.CombatAction'] ]]):
            # 1. MOVE phase
            for agent_id, move, _ in actions:
                self.apply_action(agent_id, move)

            # 2a. HUNKER phase
            for agent_id, _, combat in actions:
                if isinstance(combat, MCTS.HunkerAction):
                    self.apply_action(agent_id, combat)
            
            # 2b. COMBAT phase
            for agent_id, _, combat in actions:
                if not isinstance(combat, MCTS.HunkerAction):
                    self.apply_action(agent_id, combat)

            # 3. Remove soaked agents
            self.agents = [a for a in self.agents if a.wetness < 100]
            self.enemies = [e for e in self.enemies if e.wetness < 100]
            self.all_agents = self.agents + self.enemies
            
            # 4. Tick cooldowns
            for agent in self.all_agents:
                if agent.cooldown > 0:
                    agent.cooldown -= 1

        def get_valid_actions(self, agent: Agent) -> List[Tuple[Optional['MCTS.MoveAction'], Optional['MCTS.CombatAction']]]:
            directions = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
            positions = []

            for dx, dy in directions:
                nx, ny = agent.position.x + dx, agent.position.y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    pos = Position(nx, ny)
                    if all(pos != other.position for other in self.all_agents):
                        positions.append(pos)
            if not positions:
                positions = [agent.position]

            combat: List[Optional['MCTS.CombatAction']] = [None]

            if agent.cooldown == 0:
                for a in self.all_agents:
                    if agent.same_team( a ): continue

                    if a.wetness >= 100:
                        continue
                    if agent.position.distance_to(a.position) <= 2 * agent.metadata.opt_range:
                        combat.append(MCTS.ShootAction(a.agent_id))

            if agent.bomb_cnt > 0:
                for dx in range(-4, 5):
                    for dy in range(-4, 5):
                        if abs(dx) + abs(dy) <= 4:
                            tx, ty = agent.position.x + dx, agent.position.y + dy
                            if 0 <= tx < self.width and 0 <= ty < self.height:
                                combat.append(MCTS.ThrowAction(Position(tx, ty)))

            combat.append(MCTS.HunkerAction())

            return [(MCTS.MoveAction(pos), cb) for pos in positions for cb in combat]

        def evaluate(self) -> float:
            width, height = self.width, self.height
            control_map = [[0 for _ in range(width)] for _ in range(height)]

            def apply_influence(agent: Agent, team: int, radius: int = 6):
                if agent.wetness >= 100:
                    return
                r = radius if agent.wetness < 50 else radius // 2
                x0, y0 = agent.position.x, agent.position.y

                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        if abs(dx) + abs(dy) > r:
                            continue
                        x, y = x0 + dx, y0 + dy
                        if 0 <= x < width and 0 <= y < height:
                            if control_map[y][x] == -team:
                                control_map[y][x] = 0  # neutralize
                            elif control_map[y][x] == 0:
                                control_map[y][x] = team

            # Apply agent and enemy influence
            for a in self.agents:
                apply_influence(a, team=1)
            for e in self.enemies:
                apply_influence(e, team=-1)

            # Score control map
            tile_score = sum(1 for row in control_map for v in row if v == 1) - \
                        sum(1 for row in control_map for v in row if v == -1)

            # Other metrics
            my_alive = sum(1 for a in self.agents if a.wetness < 100)
            enemy_alive = sum(1 for e in self.enemies if e.wetness < 100)

            my_wet = sum(a.wetness for a in self.agents)
            enemy_wet = sum(e.wetness for e in self.enemies)

            agent_score = 50 * (my_alive - enemy_alive)
            wetness_score = (enemy_wet - my_wet)
            score_delta = 10 * (self.my_score - self.enemy_score)

            return score_delta + agent_score + wetness_score + tile_score

    class MCTSNode:
        def __init__(self, state: 'MCTS.MiniGameState', parent: Optional['MCTS.MCTSNode'] = None):
            self.state = state
            self.parent = parent
            self.children: List[MCTS.MCTSNode] = []
            self.visits = 0
            self.value = 0.0

            self.applied_action_plan: Optional[List[Tuple[int, MCTS.MoveAction, MCTS.CombatAction]]] = None

            # Precompute all valid per-agent actions once
            self.possible_joint_actions: List[List[Tuple[int, MCTS.MoveAction, MCTS.CombatAction]]] = []
            self._initialize_joint_actions()

        def _initialize_joint_actions(self):
            agent_actions: Dict[int, List[Tuple[MCTS.MoveAction, MCTS.CombatAction]]] = {}

            for agent in self.state.agents:
                agent_actions[agent.agent_id] = self.state.get_valid_actions(agent)

            # Naive: take first N sampled combinations (random Cartesian sampling)
            joint = []
            for agent_id, actions in agent_actions.items():
                if actions:
                    move, combat = random.choice(actions)
                    joint.append((agent_id, move, combat))

            self.possible_joint_actions.append(joint)

        def is_fully_expanded(self) -> bool:
            return len(self.possible_joint_actions) == 0

        def expand(self) -> 'MCTS.MCTSNode':
            if self.is_fully_expanded():
                raise RuntimeError("No more actions to expand.")

            action_plan = self.possible_joint_actions.pop()
            new_state = self.state.clone()
            new_state.simulate_turn(action_plan)

            child = MCTS.MCTSNode(new_state, parent=self)
            child.applied_action_plan = action_plan
            self.children.append(child)
            return child

        def best_child(self, c: float = 1.41) -> 'MCTS.MCTSNode':
            def uct_score(child: 'MCTS.MCTSNode') -> float:
                if child.visits == 0:
                    return float('inf')
                exploitation = child.value / child.visits
                exploration = c * math.sqrt(math.log(self.visits + 1) / (child.visits))
                return exploitation + exploration

            return max(self.children, key=uct_score)

        def backpropagate(self, reward: float):
            self.visits += 1
            self.value += reward
            if self.parent:
                self.parent.backpropagate(reward)

        def rollout(self) -> float:
            rollout_state = self.state.clone()
            for agent in rollout_state.agents:
                actions = rollout_state.get_valid_actions(agent)
                if actions:
                    move, combat = random.choice(actions)
                    rollout_state.apply_action(agent.agent_id, move)
                    rollout_state.apply_action(agent.agent_id, combat)

            # Also simulate enemy actions
            for enemy in rollout_state.enemies:
                actions = rollout_state.get_valid_actions(enemy)
                if actions:
                    move, combat = random.choice(actions)
                    rollout_state.apply_action(enemy.agent_id, move)
                    rollout_state.apply_action(enemy.agent_id, combat)

            return rollout_state.evaluate()

    
    @staticmethod
    def search(state: GameState, time_limit_ms: float = 45.0, turn: int = 0) -> List[Tuple[int, Optional['MCTS.MoveAction'], Optional['MCTS.CombatAction']]]:
        start = time.perf_counter()
        root_state = MCTS.MiniGameState.from_game_state(state)
        root = MCTS.MCTSNode(root_state)

        iterations = 0
        while (time.perf_counter() - start) * 1000 < time_limit_ms:
            node = root

            # 1. Selection
            while not node.is_fully_expanded() and node.children:
                node = node.best_child()

            # 2. Expansion
            if not node.is_fully_expanded():
                node = node.expand()

            # 3. Rollout
            reward = node.rollout()

            # 4. Backpropagation
            node.backpropagate(reward)
            iterations += 1

        print(f"[MCTS] Iterations: {iterations}", file=sys.stderr)

        # Exploit best child
        best = root.best_child(c=0)
        return best.applied_action_plan or []

class Game:
    def __init__(self):
        with Timer("Initialize from input"):
            self.state = GameState.from_input()

    def run(self):
        turn = 1
        while True:
            with Timer(f"Turn {turn}"):
                self.state.read_turn()
                print(self.state.debug_string(), file=sys.stderr)
                print(f"[SCORE] Me = {self.state.my_score}, Enemy = {self.state.enemy_score}, Delta = {self.state.my_score - self.state.enemy_score}", file=sys.stderr)
            
                actions = MCTS.search(self.state)

                for agent_id, move, combat in actions:
                    cmds = [f"{agent_id}"]
                    if move:
                        cmds.append(f"{move}")
                    if combat:                        
                        cmds.append(f"{combat}")
                    cmds.append("MESSAGE MCTS")
                    print(";".join(cmds), flush=True)
                
                turn += 1

Game().run()
