
import sys
import heapq
from dataclasses import dataclass

from typing import FrozenSet, List, Dict, NamedTuple, Optional, Set, Tuple

# --- Type Aliases ---
class Position(NamedTuple):
    x: int
    y: int

    def to_tuple(self) -> Tuple[int,int]:
        return (self.x, self.y)
    
    def distance_to(self, other: 'Position') -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)
    
    def __str__(self) -> str:
        return f"P({self.x},{self.y})"
    def __repr__(self):
        return self.__str__()
@dataclass
class Tile:
    position: Position
    tile_type: int  # 0 = empty, 1 = low cover, 2 = high cover

@dataclass
class AgentMeta:
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

    def __str__(self) -> str:
        prefix = "A" if self.is_friendly else "E"
        parts = [f"{prefix}{self.agent_id}@{self.position.x},{self.position.y}"]
        parts.append(f"cd={self.cooldown}")
        parts.append(f"b={self.bomb_cnt}")
        parts.append(f"w={self.wetness}")

        return " ".join(parts)

    def __repr__(self):
        return self.__str__()

Grid = List[List[Tile]]

class AStarPathfinder:
    def __init__(self, width:int, height:int, grid: Grid):
        self.width = width
        self.height = height
        self.grid = grid

    def neighbors(self, node: Position) -> Position: # type: ignore
        x, y = node
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.grid[ny][nx].tile_type == 0:
                    yield Position(nx, ny)

    def heuristic(self, a: Position, b: Position):
        return a.distance_to(b)

    def find_path(self, start: Position, goal: Position, blocked: Set[Position]):
        open_set = []
        heapq.heappush(open_set, (self.heuristic(start, goal), 0, start))
        came_from = {}
        cost_so_far = {start: 0}

        dynamic_blocked = [p for p in blocked if p != start]

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
                if neighbor in dynamic_blocked:
                    continue
                new_cost = cost + 1
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (priority, new_cost, neighbor))
                    came_from[neighbor] = current
        return [start]

class GameState:
    def __init__(self, my_id: int, width: int, height: int, grid: List[List[Tile]], blocked: Set[Position], agents_meta: Dict[int, AgentMeta]):
        self.my_id = my_id
        self.width = width
        self.height = height
        self.grid = grid
        self.blocked = blocked
        self.all_agents_meta = agents_meta
        self.pathfinder = AStarPathfinder(width, height, grid)
        self.my_agents: List[Agent] = []
        self.enemies: List[Agent] = []
        self.accessibility_map: Dict[Position, Set[Position]] = self.build_accessibility_map()

    @staticmethod
    def from_input():
        my_id = int(input())
        agent_data_count = int(input())
        agents_meta: Dict[int, AgentMeta] = {}

        for _ in range(agent_data_count):
            agent_id, player, cd, rng, power, bombs = map(int, input().split())
            agents_meta[agent_id] = AgentMeta(agent_id, player != my_id, cd, rng, power, bombs)
            

        width, height = map(int, input().split())
        grid: List[List[Optional[Tile]]] = [[None for _ in range(width)] for _ in range(height)]
        blocked: Set[Position] = set()

        for _ in range(height):
            row = input().split()
            for x in range(width):
                tx, ty, ttype = int(row[x*3]), int(row[x*3+1]), int(row[x*3+2])
                grid[ty][tx] = Tile(Position(tx, ty), ttype)
                if ttype != 0:
                    blocked.add( Position(tx, ty) )


        state = GameState(my_id, width, height, grid, blocked, agents_meta)

        return state

    def read_turn(self):
        self.my_agents.clear()
        self.enemies.clear()

        agent_count = int(input())
        for _ in range(agent_count):
            agent_id, x, y, cd, bombs, wet = map(int, input().split())
            agent = Agent(self.all_agents_meta[ agent_id], Position(x,y), cd, bombs, wet)
            if agent.metadata.is_enemy :
                self.enemies.append( agent )
            else:
                self.my_agents.append( agent )
        
        input() # read my_agent count (not needed)
    
    def build_accessibility_map(self) -> Dict[Position, Set[Position]]:
        walkable_tiles = [
            Position(x, y)
            for y in range(self.height)
            for x in range(self.width)
            if self.grid[y][x].tile_type == 0
        ]

        accessibility_map: Dict[Position, Set[Position]] = {}   
        for start in walkable_tiles:
            reachable = set()
            frontier = [start]
            visited = set()

            while frontier:
                current = frontier.pop()
                if current in visited:
                    continue
                visited.add(current)
                reachable.add(current)

                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = current.x + dx, current.y + dy
                    np = Position(nx, ny)
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        if np not in self.blocked and np not in visited:
                            frontier.append(np)

            accessibility_map[start] = reachable

        return accessibility_map

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

class CoverAnalyzer:
    def __init__(self, grid: Grid):
        self.grid = grid

    def is_adjacent_to_cover(self, p: Position) -> bool:
        
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = p.x + dx, p.y + dy
            if 0 <= nx < len(self.grid[0]) and 0 <= ny < len(self.grid):
                if self.grid[ny][nx].tile_type in (1, 2):
                    return True
        return False

    def find_best_adjacent_cover_tile( 
            self, agent_pos: Position, blocked: Set[Position], enemies: List[Agent] ) -> Optional[Position]:

        best: Optional[Position] = None
        best_score = -1

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = agent_pos.x + dx, agent_pos.y + dy
            if 0 <= nx < len(self.grid[0]) and 0 <= ny < len(self.grid):
                candidate = Position(nx, ny)
                tile = self.grid[ny][nx]

                if tile.tile_type != 0 or candidate in blocked:
                    continue

                score = 0
                for enemy in enemies:
                    dist = candidate.distance_to(enemy.position)
                    if dist > 2 * enemy.metadata.opt_range:
                        continue  # enemy can't reach even at max range

                    # Compute normalized direction from enemy to candidate
                    dx = candidate.x - enemy.position.x
                    dy = candidate.y - enemy.position.y
                    if dx != 0:
                        dx = dx // abs(dx)
                    if dy != 0:
                        dy = dy // abs(dy)

                    # Check tile "behind" candidate (between it and the enemy)
                    cx = candidate.x - dx
                    cy = candidate.y - dy
                    if 0 <= cx < len(self.grid[0]) and 0 <= cy < len(self.grid):
                        cover_tile = self.grid[cy][cx]
                        if cover_tile.tile_type == 2:
                            score += 3
                        elif cover_tile.tile_type == 1:
                            score += 2

                if score > best_score:
                    best = candidate
                    best_score = score

        return best

class Bot:
    def compute_range_multiplier(self, dist: int, opt_range: int) -> float:

        if dist > 2 * opt_range:
            return 0.0
        elif dist <= opt_range:
            return 1.0
        else:
            return 0.5

    def compute_cover_multiplier(
        self,
        shooter_pos: Position,
        target_pos: Position,
        grid: Grid
    ) -> float:
        """
        Applies max reduction from tiles adjacent to target but not adjacent to shooter.
        High cover = 0.25 (75% blocked), Low = 0.5 (50%)
        """
        max_penalty = 0
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            cx = target_pos.x + dx
            cy = target_pos.y + dy
            if 0 <= cx < len(grid[0]) and 0 <= cy < len(grid):
                tile = grid[cy][cx]
                if tile.tile_type in (1, 2):
                    if abs(shooter_pos.x - cx) + abs(shooter_pos.y - cy) > 1:
                        if tile.tile_type == 2:
                            max_penalty = max(max_penalty, 0.75)
                        elif tile.tile_type == 1:
                            max_penalty = max(max_penalty, 0.5)
        return 1.0 - max_penalty

    def compute_bomb_target(self, shooter: Agent, friendlies: List[Agent], enemies: List[Agent]) -> Optional[Position]:
        """
        Calculate best target for a bomb.
        - bomb can be thrown a distance of 4
        - bomb has a blast radius of
            - impact tile
            - all adjacent tiles (orthogonally and diagonally). 
        - do NOT throw bomb so that a friendly is in the blast radius
        - throw bomb so that maximum enemies will be hit
        """
        if not shooter.has_bombs():
            return None

        friendlies.remove( shooter )

        max_hits = 0
        best_tile = None

        # Search within 4-tile manhattan range
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                tx = shooter.position.x + dx
                ty = shooter.position.y + dy

                if tx < 0 or ty < 0: continue

                if abs(dx) + abs(dy) > 4:
                    continue  # outside bomb range

                target_tile = Position(tx, ty)

                # compute AoE splash radius (8 + center)
                aoe_tiles = [
                    Position(tx + ox, ty + oy)
                    for ox in [-1, 0, 1]
                    for oy in [-1, 0, 1]
                    if 0 <= tx + ox < 13 and 0 <= ty + oy < 5
                ]

                # don't bomb if any friendly is inside blast radius
                if any(f.position in aoe_tiles for f in friendlies):
                    continue

                hit_count = sum(1 for e in enemies if e.position in aoe_tiles)

                if hit_count > max_hits:
                    max_hits = hit_count
                    best_tile = target_tile

        return best_tile

    def compute_damage(
        self,
        shooter: Agent,
        target: Agent,
        grid: Grid
    ) -> int:

        dist = shooter.position.distance_to(target.position)
        distance_mult = self.compute_range_multiplier(dist, shooter.metadata.opt_range)
        cover_mult = self.compute_cover_multiplier(shooter.position, target.position, grid)
        dmg = int(shooter.metadata.soak_power * distance_mult * cover_mult)

        return dmg

    def decide(self, state: GameState, cover: CoverAnalyzer) -> List[str]:

        if not state.enemies:
            return [f"{a.agent_id};HUNKER_DOWN" for a in state.my_agents]

        actions = []
        blocked = set( state.blocked )

        for agent in state.my_agents:
            cmds = []
            # Find best cover to move to
            best_tile = cover.find_best_adjacent_cover_tile(agent.position, blocked, state.enemies)
            move_tile = best_tile if best_tile is not None else (agent.position)

            if move_tile != agent.position:
                agent.position = move_tile #this could cause issues when we start simulating.
                cmds.append(f"MOVE {move_tile.x} {move_tile.y}")
                blocked.add( move_tile )
            else:
                blocked.add( agent.position )

            # should we throw a bomb?
            bomb_target = self.compute_bomb_target(agent, state.my_agents, state.enemies)
            if bomb_target:
                cmds.append(f"THROW {bomb_target.x} {bomb_target.y}")
            else:
                # Find best enemy to shoot from this tile
                candidates = []
                for enemy in state.enemies:
                    dist = agent.position.distance_to(enemy.position)

                    if dist <= 2*agent.metadata.opt_range:
                        range_multi = self.compute_range_multiplier(dist, agent.metadata.opt_range)
                        cover_multi = self.compute_cover_multiplier(agent.position, enemy.position, state.grid)
                        dmg = int(agent.metadata.soak_power * range_multi * cover_multi)

                        sort_key = (-dmg, -range_multi, enemy.agent_id)
                        candidates.append((sort_key, enemy))

                candidates.sort()
                best_target = candidates[0][1] if candidates else None
                if agent.cooldown == 0 and best_target:
                    cmds.append(f"SHOOT {best_target.agent_id}")

            if not cmds:
                cmds = ["HUNKER_DOWN"]

            actions.append(f"{agent.agent_id};{';'.join(cmds)}")
            print(f"{agent.agent_id};{';'.join(cmds)}", file=sys.stderr)
            
        return actions

class BombBot:
    def __init__(self, state: GameState):
        # Store all relevant references and precalculated sets for efficiency
        self.state = state
        self.grid = state.grid
        self.agents = state.my_agents
        self.enemies = state.enemies
        self.enemy_positions = {e.position for e in self.enemies}
        self.agent_positions = {a.position for a in self.agents}
        self.blocked_static = state.blocked
        self.pathfinder = state.pathfinder
        self.width = state.width
        self.height = state.height

    def is_agent_trapped(self, agent: Agent, max_depth: int = 20) -> bool:
        """
        Returns True if the agent is surrounded by cover or enclosed by the map/walls
        with no path to any open area (within a limit of `max_depth` tiles explored).
        """
        visited = set()
        frontier = [agent.position]
        steps = 0

        while frontier and steps < max_depth:
            current = frontier.pop()
            if current in visited:
                continue
            visited.add(current)

            x, y = current.x, current.y

            # If on map edge or next to an open tile, agent is not trapped
            if x == 0 or y == 0 or x == self.width - 1 or y == self.height - 1:
                return False
            if self.grid[y][x].tile_type == 0:
                return False

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    next_pos = Position(nx, ny)
                    tile = self.grid[ny][nx]
                    if tile.tile_type == 0 and next_pos not in visited:
                        frontier.append(next_pos)

            steps += 1

        # If search finishes without finding an exit
        return True

    def get_aoe_tiles(self, center: Position) -> Set[Position]:
        return {
            Position(center.x + dx, center.y + dy)
            for dx in [-1, 0, 1]
            for dy in [-1, 0, 1]
            if 0 <= center.x + dx < self.width and 0 <= center.y + dy < self.height
        }

    def compute_candidate_targets(self) -> List[Tuple[Position, Set[int]]]:
        # Any target that would hit a friendly agent (including self) is excluded
        enemy_map = {e.position: e.agent_id for e in self.enemies}
        target_map: Dict[Position, Set[int]] = {}

        for enemy in self.enemies:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    cx, cy = enemy.position.x - dx, enemy.position.y - dy
                    center = Position(cx, cy)
                    if not (0 <= cx < self.width and 0 <= cy < self.height):
                        continue

                    aoe = self.get_aoe_tiles(center)
                    if any(pos in self.agent_positions for pos in aoe):  # exclude any target whose AoE would hit a friendly
                        continue

                    hit_ids = {eid for pos, eid in enemy_map.items() if pos in aoe}
                    if hit_ids:
                        target_map[center] = hit_ids

        sorted_targets = sorted(target_map.items(), key=lambda t: len(t[1]), reverse=True)

        # Remove overlapping AoEs by greedily claiming the best hits
        claimed_enemies = set()
        final_targets = []
        for center, hit_ids in sorted_targets:
            new_hits = hit_ids - claimed_enemies
            if new_hits:
                final_targets.append((center, hit_ids))
                claimed_enemies.update(hit_ids)

        return final_targets

    def decide(self) -> List[str]:
        actions = []
        claimed_targets: Set[FrozenSet[int]] = set()
        reserved_positions: Set[Position] = set()
        used_agents: Set[int] = set()

        candidates = self.compute_candidate_targets()
        agent_map = {a.agent_id: a for a in self.agents if a.bomb_cnt > 0}

        # PASS 1: THROW or MOVE+THROW
        for agent_id, agent in agent_map.items():
            print(f"PASS 1: planning {agent}", file=sys.stderr)
                
            if self.is_agent_trapped(agent):
                print(f"Agent {agent.agent_id} is trapped", file=sys.stderr)
                actions.append(f"{agent_id};HUNKER_DOWN")
                used_agents.add(agent_id)
                reserved_positions.add(agent.position)
                continue

            if agent.bomb_cnt == 0:
                print(f"Agent {agent.agent_id} is out of ammo", file=sys.stderr)
                actions.append(f"{agent_id};HUNKER_DOWN")
                used_agents.add(agent_id)
                reserved_positions.add(agent.position)
                continue

            for target, enemies_hit in candidates:
                enemy_key = frozenset(enemies_hit)
                if enemy_key in claimed_targets:
                    continue

                if any(pos in self.agent_positions for pos in self.get_aoe_tiles(target)):
                    continue

                if agent.position.distance_to(target) <= 4:
                    actions.append(f"{agent_id};THROW {target.x} {target.y}")
                    used_agents.add(agent_id)
                    claimed_targets.add(enemy_key)
                    reserved_positions.add(agent.position)
                    break

                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = agent.position.x + dx, agent.position.y + dy
                    move_pos = Position(nx, ny)
                    if (0 <= nx < self.width and 0 <= ny < self.height
                        and move_pos.distance_to(target) <= 4
                        and move_pos not in self.blocked_static
                        and move_pos not in self.enemy_positions
                        and move_pos not in reserved_positions):
                        actions.append(f"{agent_id};MOVE {nx} {ny};THROW {target.x} {target.y}")
                        used_agents.add(agent_id)
                        claimed_targets.add(enemy_key)
                        reserved_positions.add(move_pos)
                        break
                if agent_id in used_agents:
                    break
       
        # PASS 2: MOVE  toward closest unclaimed target center
        for agent_id, agent in agent_map.items():
            if agent_id in used_agents:
                continue

            print(f"PASS 2: planning {agent}", file=sys.stderr)

            best_target = None
            best_dist = 9999999

            for target, enemies_hit in candidates:
                enemy_key = frozenset(enemies_hit)
                if enemy_key in claimed_targets:
                    continue

                dist = agent.position.distance_to( target )
                if dist < best_dist:
                    best_target = target
                    best_dist = dist

            if best_target:
                actions.append(f"{agent_id};MOVE {best_target.x} {best_target.y}")

            else:
                actions.append(f"{agent_id};HUNKER_DOWN")

        return actions

class Game:
    def __init__(self):

        self.state = GameState.from_input()
        self.cover = CoverAnalyzer(self.state.grid)

        
    def run(self):

        while True:            
            self.state.read_turn()

            print(self.state.debug_string(), file=sys.stderr)

            actions = BombBot(self.state).decide()
            for act in actions:
                print(act, flush=True)


Game().run()
