"""
Summer 2025 CodinGame event Bot
"""
import sys
import heapq
from dataclasses import dataclass
from typing import List, Dict, NamedTuple, Optional, Set, Tuple



# --- Type Aliases ---
class Position(NamedTuple):
    """ 2D Position on map """
    x: int
    y: int

    def to_tuple(self) -> Tuple[int,int]:
        """ Convert Position to Tuple """
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

@dataclass
class Bunker:
    top_left: Position
    width: int
    height: int


    @property
    def center(self) -> Position:
        center_x = self.top_left.x + self.width // 2
        center_y = self.top_left.y + self.height // 2
        return Position(center_x, center_y)


    def __str__(self):
        return f"Bunker({self.top_left}, w:{self.width}, h:{self.height})"


    def __repr__(self):
        return self.__str__()




    @staticmethod
    def detect_bunkers(grid: Grid) -> List["Bunker"]:
        visited = set()
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        bunkers = []

        for y in range(height):
            for x in range(width):
                pos = Position(x, y)
                tile = grid[y][x]
                if tile.tile_type == 0 or pos in visited:
                    continue

                # Flood fill from cover tile
                cover_tiles = []
                queue = [pos]
                while queue:
                    p = queue.pop()
                    if p in visited:
                        continue
                    visited.add(p)
                    if grid[p.y][p.x].tile_type == 0:
                        continue
                    cover_tiles.append(p)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = p.x + dx, p.y + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            np = Position(nx, ny)
                            if np not in visited:
                                queue.append(np)

                if not cover_tiles:
                    continue

                xs = [p.x for p in cover_tiles]
                ys = [p.y for p in cover_tiles]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                w = max_x - min_x + 1
                h = max_y - min_y + 1

                # Skip tiny or malformed regions
                if w < 3 or h < 3:
                    continue

                # Check rectangle border is cover, interior is walkable
                is_bunker = True
                for yy in range(min_y, max_y + 1):
                    for xx in range(min_x, max_x + 1):
                        t = grid[yy][xx]
                        edge = (xx == min_x or xx == max_x or yy == min_y or yy == max_y)
                        if edge:
                            if t.tile_type == 0:
                                is_bunker = False
                        else:
                            if t.tile_type != 0:
                                is_bunker = False

                if is_bunker:
                    bunkers.append(Bunker(Position(min_x, min_y), w, h))

        return bunkers


    def get_agents_inside(self, all_agents: List[Agent]) -> List[Agent]:
        inside = []
        for agent in all_agents:
            px, py = agent.position.x, agent.position.y
            if (self.top_left.x < px < self.top_left.x + self.width - 1 and
                self.top_left.y < py < self.top_left.y + self.height - 1):
                inside.append(agent)
        return inside

class TacticalUtils:
    @staticmethod
    def compute_range_multiplier(dist: int, opt_range: int) -> float:
        if dist > 2 * opt_range:
            return 0.0
        elif dist <= opt_range:
            return 1.0
        else:
            return 0.5

    @staticmethod
    def compute_cover_multiplier(shooter_pos: Position, target_pos: Position, grid: Grid) -> float:
        max_penalty = 0
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            cx, cy = target_pos.x + dx, target_pos.y + dy
            if 0 <= cx < len(grid[0]) and 0 <= cy < len(grid):
                tile = grid[cy][cx]
                if tile.tile_type in (1, 2):
                    if abs(shooter_pos.x - cx) + abs(shooter_pos.y - cy) > 1:
                        if tile.tile_type == 2:
                            max_penalty = max(max_penalty, 0.75)
                        elif tile.tile_type == 1:
                            max_penalty = max(max_penalty, 0.5)
        return 1.0 - max_penalty

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


class TacticalBot:
    def __init__(self, state: GameState):
        self.state = state
        self.grid = state.grid
        self.pathfinder = state.pathfinder
        self.cover = CoverAnalyzer(self.grid)
        
    def evaluate_tile_danger(self, tile: Position) -> int:
        danger = 0
        for enemy in self.state.enemies:
            if enemy.cooldown > 0:
                continue
            dist = tile.distance_to(enemy.position)
            if dist > 2 * enemy.metadata.opt_range:
                continue

            range_mult = TacticalUtils.compute_range_multiplier(dist, enemy.metadata.opt_range)
            cover_mult = TacticalUtils.compute_cover_multiplier(enemy.position, tile, self.grid)
            damage = int(enemy.metadata.soak_power * range_mult * cover_mult)
            danger += damage
        return danger

    def find_best_cover_tile(self, agent: Agent, max_depth: int = 6) -> Optional[Position]:
        """
        Forward-biased best cover tile search.
        Prioritizes tiles with cover, low danger, and forward progress toward enemy lines.
        """
        visited = set()
        frontier = [(agent.position, 0)]
        best_tile = None
        best_score = float('inf')

        while frontier:
            current, depth = frontier.pop(0)
            if depth > max_depth or current in visited:
                continue
            visited.add(current)

            tile = self.grid[current.y][current.x]
            if tile.tile_type != 0:
                continue

            if self.cover.is_adjacent_to_cover(current):
                danger = self.evaluate_tile_danger(current)
                avg_enemy_y = sum(e.position.y for e in self.state.enemies) / len(self.state.enemies) if self.state.enemies else current.y
                forward_bias = -(avg_enemy_y - current.y)
                score = danger + forward_bias
                if score < best_score:
                    best_score = score
                    best_tile = current

            for neighbor in self.pathfinder.neighbors(current):
                if neighbor not in visited:
                    frontier.append((neighbor, depth + 1))

        return best_tile

    def find_best_bomb_target(self, agent: Agent) -> Optional[Position]:
        if not agent.has_bombs():
            return None

        max_hits = 0
        best_tile = None
        friendly_positions = {a.position for a in self.state.my_agents }

        for dx in range(-4, 5):
            for dy in range(-4, 5):
                tx, ty = agent.position.x + dx, agent.position.y + dy
                if abs(dx) + abs(dy) > 4:
                    continue
                if not (0 <= tx < self.state.width and 0 <= ty < self.state.height):
                    continue
                center = Position(tx, ty)
                aoe = [
                    Position(tx + ox, ty + oy)
                    for ox in [-1, 0, 1]
                    for oy in [-1, 0, 1]
                    if 0 <= tx + ox < self.state.width and 0 <= ty + oy < self.state.height
                ]
                if any(pos in friendly_positions for pos in aoe):
                    continue
                hits = sum(1 for e in self.state.enemies if e.position in aoe)
                if hits > max_hits:
                    max_hits = hits
                    best_tile = center
        return best_tile

    def find_best_shot(self, agent: Agent) -> Optional[int]:
        
        best_target = None
        best_damage = -1
        for enemy in self.state.enemies:
            dist = agent.position.distance_to(enemy.position)
            if dist <= 2 * agent.metadata.opt_range:
                range_mult = TacticalUtils.compute_range_multiplier(dist, agent.metadata.opt_range)
                cover_mult = TacticalUtils.compute_cover_multiplier(agent.position, enemy.position, self.grid)
                damage = int(agent.metadata.soak_power * range_mult * cover_mult)
                if damage > best_damage:
                    best_damage = damage
                    best_target = enemy.agent_id
        return best_target

    def decide(self) -> List[str]:
        actions = []

        for agent in self.state.my_agents:
            msg = ""
            if agent.cooldown > 0:
                msg = f";MESSAGE Reloading {agent.cooldown}"

            cmds = []
            attacked = False

            blocked = self.state.blocked.copy().union(
                [a.position for a in self.state.enemies],
                [a.position for a in self.state.my_agents if a.agent_id != agent.agent_id])

            best_tile = self.find_best_cover_tile(agent)
            if best_tile and best_tile != agent.position:
                path = self.pathfinder.find_path(agent.position, best_tile, blocked)
                if len(path) > 1:
                    step = path[1]
                    cmds.append(f"MOVE {step.x} {step.y}")
                    blocked.add(step)
                    agent.position = step
                else:
                    blocked.add(agent.position)
            else:
                blocked.add(agent.position)

            bomb_target = self.find_best_bomb_target(agent)
            if bomb_target:
                cmds.append(f"THROW {bomb_target.x} {bomb_target.y}")
                attacked = True
            else:
                if agent.cooldown == 0:
                    target_id = self.find_best_shot(agent)
                    if target_id is not None:
                        cmds.append(f"SHOOT {target_id}")
                        attacked = True

            if not attacked:
                cmds.append("HUNKER_DOWN")

            actions.append(f"{agent.agent_id};{';'.join(cmds)}{ msg }")
            print(f"{agent.agent_id};{';'.join(cmds)}", file=sys.stderr)

        return actions

class Game:
    def __init__(self):
        self.state = GameState.from_input()
        self.cover = CoverAnalyzer(self.state.grid)
        
    def run(self):
        """ Run game """

        while True:
            self.state.read_turn()
            print(self.state.debug_string(), file=sys.stderr)

            actions = TacticalBot(self.state).decide()
            for act in actions:
                print(act, flush=True)


Game().run()
