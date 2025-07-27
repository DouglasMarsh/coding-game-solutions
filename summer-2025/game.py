from enum import IntFlag, auto
import math
import random
import sys
import heapq
from dataclasses import dataclass
from typing import List, Dict, NamedTuple, Optional, Set, Tuple, Union
import time
import base64


class DebugFlag(IntFlag):
    NONE = 0
    INIT = auto()  # Assigns 1
    TIMER = auto() # Assigns 2
    STATE = auto() # Assigns 4
    SCORE = auto()
    TACTICAL = auto()
    MCTS = auto()
    TURN = auto()
    ALL = INIT | TIMER | STATE | SCORE | TACTICAL | MCTS | TURN
class DebugLogger:
    def __init__(self, enable=True, flags = DebugFlag.ALL, enable_cache = True):
        self.enable = enable
        self.enabled_flags = flags
        self.enable_cache = enable_cache
        self.cache = []        
        self.turn = 0

    def set_turn(self, turn):
        if self.turn > 0:
            self.log(DebugFlag.TURN, f"[END TURN] {self.turn}", False)
            
        self.turn = turn
        self.log(DebugFlag.TURN, f"[START TURN] {turn}", False)
    
    def log(self, flag: DebugFlag, msg: str, print_flag = True):
        if not self.enable:
            return
        if not flag in self.enabled_flags:
            return
        
        name = f"[{flag.name}] - "
        if not print_flag:
            name = ""
        
        if self.enable_cache:
            self.cache.append(f"{name}{msg}")
        else:
            print(f"{name}{msg}", file=sys.stderr)

    def flush_encoded(self):
        if not self.enable or not self.cache:
            return
        combined = '\n'.join(self.cache)
        compressed = base64.b64encode(combined.encode()).decode()
        print(f"[ENDLOG]\n{compressed}", file=sys.stderr)

    def flush_tail(self, lines=100):
        if not self.enable or not self.cache:
            return
        print("===== FINAL DEBUG TAIL =====", file=sys.stderr)
        for line in self.cache[-lines:]:
            print(line, file=sys.stderr)

logger = DebugLogger( 
    True, enable_cache=False, 
    flags=DebugFlag.INIT|DebugFlag.STATE|DebugFlag.SCORE|DebugFlag.TACTICAL )

class Timer:
    def __init__(self, label):
        self.label = label
        self.start = None

    def __enter__(self):
        self.start = time.perf_counter()

    def __exit__(self, *args):
        elapsed = (time.perf_counter() - self.start) * 1000
        logger.log(DebugFlag.TIMER, f"{self.label}: {elapsed:.3f}ms")

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
    player_id: int
    agent_id: int
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

    def __hash__(self):
        return self.agent_id

    @property
    def agent_id(self) -> int:
        return self.metadata.agent_id

    @property
    def is_enemy(self, a: 'Agent') -> bool:
        return self.metadata.player_id != a.metadata.player_id

    @property
    def is_friendly(self, a: 'Agent') -> bool:
        return not self.is_enemy(a)

    def has_bombs(self) -> bool:
        return self.bomb_cnt > 0
    
    def clone(self):
        return Agent(self.metadata, self.position, self.cooldown, self.bomb_cnt, self.wetness)

Grid = List[List[Tile]]

class Util:
    @staticmethod
    def compute_tile_control_and_agent_maps(
        width: int,
        height: int,
        agents: List[Agent],
        my_id: int
    ) -> Tuple[List[List[int]], Set[Position], Set[Position], Set[Position], Dict[int, Dict[Position, int]]]:

        all_tiles: Set[Position] = {
            Position(x, y) for y in range(height) for x in range(width)
        }

        per_agent_maps: Dict[int, Dict[Position, int]] = {
            agent.agent_id: {} for agent in agents if agent.wetness < 100
        }

        my_tiles: Set[Position] = set()
        enemy_tiles: Set[Position] = set()
        neutral_tiles: Set[Position] = set()
        tile_control: List[List[int]] = [[-1 for _ in range(width)] for _ in range(height)]

        for pos in all_tiles:
            best_dist = float('inf')
            owner: int = -1

            for agent in agents:
                if agent.wetness >= 100:
                    continue

                dist = agent.position.distance_to( pos )
                per_agent_maps[agent.agent_id][pos] = dist

                if agent.wetness >= 50:
                    dist *= 2
                
                if dist < best_dist:
                    best_dist = dist
                    owner = agent.metadata.player_id
                elif dist == best_dist:
                    if owner != agent.metadata.player_id:
                        owner = -1  # contested

            tile_control[pos.y][pos.x] = owner
            if owner == -1:
                neutral_tiles.add(pos)                
            elif owner == my_id:
                my_tiles.add(pos)
            else:
                enemy_tiles.add(pos)

        return tile_control, my_tiles, enemy_tiles, neutral_tiles, per_agent_maps
    
    @staticmethod
    def get_aoe(center: Position) -> Set[Position]:
        cx, cy = center
        return {Position(cx + dx, cy + dy) for dx in range(-1, 2) for dy in range(-1, 2)}    
    
    @staticmethod
    def aoe_centers_including_point(p:Position) -> List[Tuple[Position,Set[Position]]]:
        """
        Returns all center coordinates (cx, cy) of 3x3 AOEs that include the point (x, y).
        Each AOE is centered on a point and extends 1 unit in all directions.
        """
        x, y = p.x, p.y
        return [
            (Position(x + dx, y + dy), Util.get_aoe(Position(x + dx, y + dy) ) ) for dx in range(-1, 2) for dy in range(-1, 2)]
    
    @staticmethod
    def compute_danger_map(
        width: int,
        height: int,
        grid: Grid,
        enemies: List[Agent]
    ) -> Dict[Position, int]:
        
        danger_map:Dict[Position, int] = {}

        for enemy in enemies:
            if enemy.cooldown > 0 or enemy.wetness >= 100:
                continue

            opt_range = enemy.metadata.opt_range
            max_range = 2 * opt_range
            soak = enemy.metadata.soak_power
            ex, ey = enemy.position.x, enemy.position.y

            for dx in range(-max_range, max_range + 1):
                for dy in range(-max_range, max_range + 1):
                    if abs(dx) + abs(dy) > max_range:
                        continue

                    tx, ty = ex + dx, ey + dy
                    if not (0 <= tx < width and 0 <= ty < height):
                        continue

                    dist = abs(dx) + abs(dy)
                    if dist > max_range:
                        continue

                    damage = soak if dist <= opt_range else soak // 2

                    # Compute cover reduction
                    cover_mult = 1.0
                    # Vector from enemy to target
                    step_x = 0 if dx == 0 else dx // abs(dx)
                    step_y = 0 if dy == 0 else dy // abs(dy)
                    between_x = tx - step_x
                    between_y = ty - step_y

                    if 0 <= between_x < width and 0 <= between_y < height:
                        cover_tile = grid[between_y][between_x]
                        if cover_tile.tile_type == 2:
                            cover_mult = 0.25
                        elif cover_tile.tile_type == 1:
                            cover_mult = 0.5

                    reduced_damage = int(damage * cover_mult)
                    pos = Position(tx, ty)
                    danger_map[pos] = danger_map.get(pos, 0) + reduced_damage

        return danger_map

    @staticmethod
    def compute_cover_bonus(shoot_pos: Position, target_pos: Position, grid: Grid) -> float:
        """
        Returns the cover bonus for type at target_pos from shoot_pos.
        0 = empty, 1 = low cover, 2 = high cover
        """
        dx = target_pos.x - shoot_pos.x
        dy = target_pos.y - shoot_pos.y
        best_modifier = 1.0

        for d in [(dx, 0), (0, dy)]:
            if abs(d[0]) > 1 or abs(d[1]) > 1:
                adj_x = -1 if d[0] < 0 else (1 if d[0] > 0 else 0)
                adj_y = -1 if d[1] < 0 else (1 if d[1] > 0 else 0)
                cover_pos = Position(target_pos.x + adj_x, target_pos.y + adj_y)

                if 0 <= cover_pos.x < len(grid[0]) and 0 <= cover_pos.y < len(grid):
                    cover_tile = grid[cover_pos.y][cover_pos.x]
                    if cover_tile.tile_type == 1:  # Low cover
                        best_modifier = min(best_modifier, 0.5)
                    elif cover_tile.tile_type == 2:  # High cover
                        best_modifier = min(best_modifier, 0.25)

        return best_modifier
    
    @staticmethod
    def compute_enemy_threat_level(enemy: Agent, friendly_positions: Set[Position], grid: Grid) -> float:
        """
        Computes the threat level of an enemy agent based on various factors.
        
        :param enemy: The enemy agent to evaluate.
        :param friendly_positions: Positions of friendly agents.
        :param grid: The game grid.
        :return: A float representing the threat level of the enemy.
        """
        # Proximity to friendly agents
        closest_distance = min(enemy.position.distance_to(pos) for pos in friendly_positions)
        proximity_score = 1 / (1 + closest_distance)  # Higher score for closer enemies

        # Cooldown status
        cooldown_score = 1 if enemy.cooldown == 0 else 0

        # Bomb availability
        bomb_score = 1 if enemy.has_bombs() else 0

        # Wetness level (lower wetness means higher threat)
        wetness_score = (100 - enemy.wetness) / 100

        # Positioning (cover bonus)
        cover_bonus = Util.compute_cover_bonus(enemy.position, enemy.position, grid)
        position_score = 1 - cover_bonus  # Higher score for less cover

        # Combine factors with weights
        threat_level = (
            2 * proximity_score +  # Proximity is weighted higher
            1.5 * cooldown_score +
            1.5 * bomb_score +
            1 * wetness_score +
            1 * position_score
        )

        return threat_level
    
    @staticmethod
    def compute_strategic_value(
        position: Position,
        target_tiles: Set[Position],
        danger_map: Dict[Position, int],
        friendly_positions: Set[Position],
        grid: Grid
    ) -> float:
        """
        Computes the strategic value of a position based on various factors.

        :param position: The position to evaluate.
        :param target_tiles: Set of neutral tiles.union(enemy_tiles)
        :param danger_map: Map of danger levels for each position.
        :param friendly_positions: Positions of friendly agents.
        :param grid: The game grid.
        :return: A float representing the strategic value of the position.
        """

        # Control score: prioritize positions that can shift control to your side
        control_score = 1 if position in target_tiles else 0

        # Proximity to objectives: prioritize positions near neutral or enemy tiles
        objective_distance = min(
            position.distance_to(obj) for obj in target_tiles
        ) if target_tiles else float('inf')
        objective_score = 1 / (1 + objective_distance)

        # Cover bonus: prioritize positions with better cover
        cover_bonus = Util.compute_cover_bonus(position, position, grid)

        # Danger level: avoid positions with high danger
        danger_level = danger_map.get(position, 0)
        danger_score = -danger_level

        # Proximity to allies: prioritize positions near friendly agents
        ally_distance = min(
            position.distance_to(ally) for ally in friendly_positions
        ) if friendly_positions else float('inf')
        ally_score = 1 / (1 + ally_distance)

        # Chokepoint score: prioritize positions that restrict enemy movement
        # (For simplicity, assume chokepoints are positions with fewer than 2 neighbors)
        neighbors = [
            Position(position.x + dx, position.y + dy)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
            if 0 <= position.x + dx < len(grid[0]) and 0 <= position.y + dy < len(grid)
        ]
        chokepoint_score = 1 if len(neighbors) <= 2 else 0

        # Combine factors with weights
        strategic_value = (
            2 * control_score +
            1.5 * objective_score +
            1 * cover_bonus +
            1 * danger_score +
            1.5 * ally_score +
            1 * chokepoint_score
        )

        return strategic_value
    
class AStarPathfinder: 
    def __init__(self, width: int, height: int, static_blocked: Set[Position], grid: Grid):
        self.width = width
        self.height = height
        self.static_blocked = static_blocked
        self.grid = grid

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

    def heuristic(self, a: Position, b: Position, agent_positions: Set[Position]) -> int:
        base_cost = a.distance_to(b)
        tile = self.grid[a.y][a.x]
        cover_bonus = -tile.tile_type *2        

        # Discourage proximity to other agents
        proximity_penalty = sum(max(0, 3 - a.distance_to(agent)) for agent in agent_positions)

        return base_cost + cover_bonus + proximity_penalty

    def find_path(
        self, start: Position, goal: Position, dynamic_blocked: Set[Position], agent_positions: Set[Position]
    ) -> List[Position]:
        with Timer(f"A* {start.to_tuple()} -> {goal.to_tuple()}"):
            blocked = self.static_blocked | dynamic_blocked

            open_set = []
            heapq.heappush(open_set, (self.heuristic(start, goal, agent_positions), 0, start))
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
                        priority = new_cost + self.heuristic(neighbor, goal, agent_positions)
                        heapq.heappush(open_set, (priority, new_cost, neighbor))
                        came_from[neighbor] = current

            return [start]

class GameState:
    """GameState object"""
    def __init__(self, my_id: int, width: int, height: int, grid: List[List[Tile]], blocked: Set[Position], agents_meta: Dict[int, AgentMeta]):
        self.my_id = my_id
        self.width = width
        self.height = height
        self.grid = grid
        self.blocked = blocked
        self.all_agents_meta = agents_meta
        self.pathfinder = AStarPathfinder(width, height, blocked, grid)
        self.my_agents: List[Agent] = []
        self.enemies: List[Agent] = []
        self.my_score = 0
        self.enemy_score = 0
        self.agent_dist_map: Dict[int, Dict[Position, int]] = {}
        self.my_tiles: Set[Position] = set()
        self.enemy_tiles: Set[Position] = set()
        self.neutral_tiles: Set[Position] = set()
        self.tile_control: List[List[int]] = []
        self.my_danger_map: Dict[Position, int] = {}


    @staticmethod
    def from_input():
        logger.log(DebugFlag.INIT, "[INITILIZATION]", False)
        my_id = int(input())
        logger.log(DebugFlag.INIT,my_id, False)
        agent_data_count = int(input())
        logger.log(DebugFlag.INIT,agent_data_count, False)

        agents_meta: Dict[int, AgentMeta] = {}

        for _ in range(agent_data_count):
            _in = input()
            logger.log(DebugFlag.INIT,_in, False)
            agent_id, player_id, cd, rng, power, bombs = map(int, _in.split())
            agents_meta[agent_id] = AgentMeta(player_id, agent_id, cd, rng, power, bombs)


        _in = input()
        logger.log(DebugFlag.INIT,_in, False)
        width, height = map(int, _in.split())
        grid: List[List[Optional[Tile]]] = [[None for _ in range(width)] for _ in range(height)]
        blocked: Set[Position] = set()

        for _ in range(height):       
            _in = input()
            logger.log(DebugFlag.INIT,_in, False)
            row = _in.split()
            for x in range(width):
                tx, ty, ttype = int(row[x*3]), int(row[x*3+1]), int(row[x*3+2])
                grid[ty][tx] = Tile(Position(tx, ty), ttype)
                if ttype != 0:
                    blocked.add(Position(tx, ty))

        state = GameState(my_id, width, height, grid, blocked, agents_meta)

        return state
    
    def compute_scores(self):
        delta = len(self.my_tiles) - len(self.enemy_tiles)
        turn_my_score = max(0, delta)
        turn_enemy_score = max(0, -delta)

        self.my_score += turn_my_score
        self.enemy_score += turn_enemy_score
    
    def read_turn(self):
        self.my_agents.clear()
        self.enemies.clear()

        agent_count = int(input())
        for _ in range(agent_count):
            agent_id, x, y, cd, bombs, wet = map(int, input().split())
            agent = Agent(self.all_agents_meta[agent_id], Position(x, y), cd, bombs, wet)
            if agent.metadata.player_id != self.my_id:
                self.enemies.append(agent)
            else:
                self.my_agents.append(agent)

        # Read my_agent_cnt but ignore it
        input()

        self.tile_control, self.my_tiles, self.enemy_tiles, self.neutral_tiles, self.agent_dist_map = \
            Util.compute_tile_control_and_agent_maps(
                width=self.width,
                height=self.height,
                agents=self.my_agents + self.enemies,
                my_id=self.my_id
            )
        
        self.compute_scores()
        self.my_danger_map = Util.compute_danger_map(self.width, self.height, self.grid, self.enemies)

    def debug_tile_control(self) -> str:
        if not logger.enable or DebugFlag.STATE not in logger.enabled_flags:
            return None
        
        lines = []
        for y in range(self.height):
            row_str = f"{y}: "
            for x in range(self.width):
                owner = self.tile_control[y][x]
                if owner == -1:
                    row_str += "N"
                else:
                    row_str += str(owner)
            
            lines.append(row_str.strip())
        
        return "\n".join( lines )

    def debug_string(self) -> str:
        if not logger.enable or DebugFlag.STATE not in logger.enabled_flags:
            return None
        
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
    def __init__(self, state: GameState, enemy_mode: bool = False):       
        self.enemy_mode = enemy_mode
        self.state = state
        self.grid = state.grid
        self.pathfinder = state.pathfinder
         

    @property
    def my_agents(self):
        if self.enemy_mode:
            return self.state.enemies
        return self.state.my_agents
    @property
    def enemies(self):
        if self.enemy_mode:
            return self.state.my_agents
        return self.state.enemies
    
    @property
    def my_score(self):
        if self.enemy_mode:
            return self.state.enemy_score
        return self.state.my_score
    @property
    def enemy_score(self):
        if self.enemy_mode:
            return self.state.my_score
        return self.state.enemy_score           

    def find_best_target_tile(
        self,
        agent: Agent,
        target_tiles: Set[Position],
        agent_map: Dict[Position, int]
    ) -> Optional[Position]:
        best_tile = None
        best_dist = float('inf')

        for pos in target_tiles:
            dist = agent_map.get(pos, float('inf'))
            if dist < best_dist:
                best_dist = dist
                best_tile = pos

        logger.log(DebugFlag.TACTICAL, f"Agent {agent.agent_id} @ {agent.position.to_tuple()} targeting {best_tile}")
        return best_tile
    
    def find_best_strategic_tile(
        self,
        agent: Agent,
        target_tiles: Set[Position],
        danger_map: Dict[Position, int],
        friendly_positions: Set[Position]
    ) -> Optional[Position]:
        best_tile = None
        best_value = float('-inf')

        for pos in target_tiles:
            value = Util.compute_strategic_value(
                pos,
                target_tiles,
                danger_map,
                friendly_positions,
                self.grid
            )
            if value < best_value:
                best_value = value
                best_tile = pos

        logger.log(DebugFlag.TACTICAL, f"Agent {agent.agent_id} @ {agent.position.to_tuple()} targeting {best_tile}")
        return best_tile
        
    
    def decide(self) -> List[str]:
        def get_shoot_dmg(agent_pos, enemy_pos, opt_range, power):
            dist = agent_pos.distance_to(enemy_pos)
            if dist <= 2 * opt_range:
                range_mult = 1.0 if dist <= opt_range else 0.5
                raw_dmg = int(power * range_mult)
                
                return raw_dmg
            return 0
        
        def get_best_shoot_target(agent:Agent, enemies: Dict[Agent, int], friendly_positions: Set[Position]) -> Optional[Tuple[Agent, int]]:
            best_target: Optional[Tuple[Agent, int, int]] = None
            for enemy, wetness in enemies.items():
                if wetness >= 100: 
                    continue

                damage = get_shoot_dmg(agent.position, enemy.position, agent.metadata.opt_range, agent.metadata.soak_power)
                if damage <= 0:
                    continue

                damage *= Util.compute_cover_bonus(agent.position, enemy.position, self.grid)

                # Prioritize targets close to elimination
                elimination_bonus = 100 if wetness + damage >= 100 else 0
                # Consider threat level (e.g., cooldown and bomb count)
                threat_level = Util.compute_enemy_threat_level(enemy, friendly_positions, self.grid)

                # Avoid overkill by checking if another agent is targeting the same enemy
                overkill_penalty = -50 if enemy.agent_id in bombed_enemies else 0

                damage_score = damage + wetness + elimination_bonus + threat_level + overkill_penalty
                if best_target is None:
                    best_target = (enemy, damage + wetness,  damage_score)
                elif damage_score > best_target[2]:
                    best_target = (enemy, damage + wetness,  damage_score)

            return best_target[0], best_target[1] if best_target else None
            
        def get_best_bomb_target(
            start: Position,
            friendlies: Set[Position],
            targets: Dict[Position, int]
        ) -> Tuple[Position, int]:
            
            valid_targets: List[Tuple[int, Position]] = []
            for pos, wetness in targets.items():
                if wetness >= 100:
                    continue

                logger.log(DebugFlag.TACTICAL, f"Evaluating bomb target {pos.to_tuple()} with wetness {wetness}")
                candidates = Util.aoe_centers_including_point(pos)
                for center, aoe in candidates:
                    dist = start.distance_to(center)
                    if dist > 4:
                        logger.log(DebugFlag.TACTICAL, f"{start.to_tuple()}: {center.to_tuple()} is out of range. {dist}")
                        continue
                   
                    if any(pos in friendlies for pos in aoe):
                        logger.log(DebugFlag.TACTICAL, f"{center.to_tuple()}: friendly in AOE {[p.to_tuple() for p in aoe]}")
                        continue
                    

                    total_wetness = sum(w + 30 for p, w in targets.items() if p in aoe)
                    valid_targets.append((total_wetness, center))


            logger.log(DebugFlag.TACTICAL, f"Valid bomb targets: {[f'{p.to_tuple()} w={w}' for w, p in valid_targets]}")
            if len(valid_targets) == 0:
                return (None, -1)

            valid_targets = sorted(valid_targets, key=lambda x: (-x[0], x[1] in targets))
            target =  valid_targets[0]
            logger.log(DebugFlag.TACTICAL, f"Best bomb target: {target[1].to_tuple()} with total wetness {target[0]}")
            return (target[1], target[0])
        
        with Timer("decide"):
            actions = []
            blocked = set(a.position for a in self.my_agents + self.enemies).union(self.state.blocked)
            target_tiles = self.state.neutral_tiles.union(self.state.enemy_tiles)
            bombed_enemies: Dict[int, Tuple[Agent, int]] = {} 
            shoot_enemies: Dict[Agent, int] = {e: e.wetness for e in self.enemies if e.wetness < 100}
            agent_positions = { a.agent_id: a.position for a in self.my_agents }
            
            for agent in self.my_agents:
                with Timer(f"decide for Agent {agent.agent_id}"):
                    cmds = []
                    attacked = False
                    move_step = None

                    target_tile = self.find_best_strategic_tile(
                        agent,
                        target_tiles,
                        self.state.my_danger_map,
                        set(agent_positions.values())
                    ) 
                    
                    if target_tile:
                        path = self.state.pathfinder.find_path(
                            agent.position, target_tile, blocked, set(agent_positions.values()))
                        if path and len(path) > 1 :
                            move_step = path[1]
                            target_tiles.remove(target_tile)

                    logger.log(DebugFlag.TACTICAL, f"Agent {agent.agent_id} @ {agent.position.to_tuple()} moving to {move_step}")
                    if move_step and move_step != agent.position:
                        cmds.append(f"MOVE {move_step.x} {move_step.y}")
                        blocked.remove( agent.position )
                        blocked.add(move_step)
                    
                    if move_step:
                        agent_positions[agent.agent_id] = move_step
                    
                    friendly_positions = set(agent_positions.values())

                    agent_pos = agent_positions[agent.agent_id]
                    if agent.has_bombs():
                        enemy_bomb_targets = {e.position: e.wetness for e in self.enemies if e.wetness < 100}
                        logger.log(DebugFlag.TACTICAL, f"Agent {agent.agent_id} enemy bomb targets: {[(p.to_tuple(), w) for p,w in enemy_bomb_targets.items()]}")
                        bomb_target, total_wetness = get_best_bomb_target(
                            agent_pos,
                            friendly_positions,
                            enemy_bomb_targets
                        )
                        if bomb_target:
                            logger.log(DebugFlag.TACTICAL, f"Agent {agent.agent_id} throwing bomb at {bomb_target.to_tuple()} with total wetness {total_wetness}")
                            cmds.append(f"THROW {bomb_target.x} {bomb_target.y}")
                            aoe = Util.get_aoe(bomb_target)
                            for e in self.enemies:
                                if e.position in aoe:
                                    bombed_enemies[e.agent_id] = (e, e.wetness + 30)
                            attacked = True                        
                
                    if agent.cooldown == 0:
                        best_shoot_target = get_best_shoot_target(agent, shoot_enemies, friendly_positions)
                        if best_shoot_target:
                            shoot_enemies[best_shoot_target[0]] = best_shoot_target[1]
                            cmds.append(f"SHOOT {best_shoot_target[0].agent_id}")
                            attacked = True

                    if not attacked:
                        cmds.append("HUNKER_DOWN")

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

            logger.log(DebugFlag.MCTS, f"[EVAL] Tile: {tile_score}, Agents: {agent_score}, Wetness: {wetness_score}, ScoreDelta: {score_delta}")
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

            score = rollout_state.evaluate()
            logger.log(DebugFlag.MCTS, f"Rollout score: {score:.2f}")
            return score


    
    @staticmethod
    def search(state: GameState, time_limit_ms: float = 45.0) -> List[Tuple[int, Optional['MCTS.MoveAction'], Optional['MCTS.CombatAction']]]:
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

        logger.log(DebugFlag.MCTS, f"Iterations: {iterations}")

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
            logger.set_turn( turn )
            with Timer(f"Turn {turn}"):
                self.state.read_turn()
                logger.log(DebugFlag.TURN, f"{turn:03d}")
                logger.log(DebugFlag.STATE, f"\n{self.state.debug_string()}")
                logger.log(DebugFlag.STATE, f"\n{self.state.debug_tile_control()}")
                logger.log(DebugFlag.SCORE, f"Me = {self.state.my_score}, Enemy = {self.state.enemy_score}, Delta = {self.state.my_score - self.state.enemy_score}")

                if turn >= 100 or abs(self.state.my_score - self.state.enemy_score) >= 600 or not self.state.enemies:
                    logger.flush_encoded()  # or use .flush_tail() for plain text
                    break

                bot = TacticalBot(self.state)


                actions = bot.decide()
                for act in actions:
                    print(act, flush=True)
                
                logger.flush_tail()
                turn += 1


Game().run()
