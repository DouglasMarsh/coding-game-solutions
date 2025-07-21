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
        self.bunkers: List[Bunker] = Bunker.detect_bunkers( grid )


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


        lines.append("\n[BUNKERS]")
        for b in self.bunkers:
            lines.append(f"{b}")
            
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
        self.state = state
        self.grid = state.grid
        self.agents = state.my_agents
        self.enemies = state.enemies
        self.pathfinder = state.pathfinder
        self.width = state.width
        self.height = state.height
        self.blocked = state.blocked
        self.all_agents = self.agents + self.enemies
        self.bunkers = [
            b for b in Bunker.detect_bunkers(self.grid)
            if not any(a.is_friendly for a in b.get_agents_inside(self.all_agents))
        ]


    def in_bunker(self, agent: Agent) -> bool:
        for bunker in self.bunkers:
            if (bunker.top_left.x <= agent.position.x < bunker.top_left.x + bunker.width and
                bunker.top_left.y <= agent.position.y < bunker.top_left.y + bunker.height):
                return True
        return False


    def best_bomb_target(self, bunker: Bunker) -> Optional[Tuple[Position, int]]:
        """Returns (target_tile, hit_count) inside bunker"""
        best_tile = None
        max_hits = -1
        enemy_positions = {e.position for e in self.enemies}


        for dx in range(1, bunker.width - 1):
            for dy in range(1, bunker.height - 1):
                tx = bunker.top_left.x + dx
                ty = bunker.top_left.y + dy
                center = Position(tx, ty)
                aoe = [
                    Position(tx + ox, ty + oy)
                    for ox in [-1, 0, 1]
                    for oy in [-1, 0, 1]
                    if 0 <= tx + ox < self.width and 0 <= ty + oy < self.height
                ]
                hits = sum(1 for pos in aoe if pos in enemy_positions)
                if hits > max_hits:
                    best_tile = center
                    max_hits = hits


        return (best_tile, max_hits) if best_tile else None


    def decide(self) -> List[str]:
        actions = []

        for agent in self.agents:
            if self.in_bunker(agent):
                print(f"[DEBUG] Agent {agent.agent_id} is inside a bunker at {agent.position}, hunkering down.", file=sys.stderr)
                actions.append(f"{agent.agent_id};HUNKER_DOWN")
                continue

            # Find closest valid bunker with enemies
            best_bunker = None
            best_target_tile = None
            min_dist = float("inf")

            for bunker in self.bunkers:
                if not bunker.get_agents_inside(self.enemies):
                    continue
                result = self.best_bomb_target(bunker)
                if not result:
                    continue
                target_tile, _ = result
                dist = agent.position.distance_to(target_tile)
                if dist < min_dist:
                    best_bunker = bunker
                    best_target_tile = target_tile
                    min_dist = dist

            if not best_bunker or not best_target_tile:
                print(f"[DEBUG] Agent {agent} has no target. HUNKER_DOWN", file=sys.stderr)                
                actions.append(f"{agent.agent_id};HUNKER_DOWN")
                continue

            # Already in range to throw
            if min_dist <= 4:
                actions.append(f"{agent.agent_id};THROW {best_target_tile.x} {best_target_tile.y}")
                continue

            # Try moving one step closer
            best_step = None
            step_dist = min_dist
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = agent.position.x + dx, agent.position.y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    tile = self.grid[ny][nx]
                    pos = Position(nx, ny)
                    if tile.tile_type == 0 and pos not in self.blocked:
                        d = pos.distance_to(best_target_tile)
                        if d < step_dist:
                            best_step = pos
                            step_dist = d

            if best_step and step_dist <= 4:
                actions.append(f"{agent.agent_id};MOVE {best_step.x} {best_step.y};THROW {best_target_tile.x} {best_target_tile.y}")
            elif best_step:
                actions.append(f"{agent.agent_id};MOVE {best_step.x} {best_step.y}")
            else:
                actions.append(f"{agent.agent_id};HUNKER_DOWN")

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