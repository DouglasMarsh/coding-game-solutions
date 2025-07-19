import sys
import time
import heapq
from dataclasses import dataclass

from typing import List, Dict, NamedTuple, Optional, Set, Tuple

# --- Type Aliases ---
class Position(NamedTuple):
    x: int
    y: int

    def to_tuple(self) -> Tuple[int,int]:
        return (self.x, self.y)
    
    def distance_to(self, other: 'Position') -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)

@dataclass
class AgentMeta:
    is_enemy: bool
    shoot_cd: int
    opt_range: int
    soak_power: int
    splash_bombs: int

@dataclass
class Agent:
    agent_id: int
    position: Position
    cooldown: int
    splash: int
    wetness: int
    metadata: AgentMeta

@dataclass
class Tile:
    position: Position
    tile_type: int  # 0 = empty, 1 = low cover, 2 = high cover


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
            agents_meta[agent_id] = AgentMeta(player != my_id, cd, rng, power, bombs)
            

        width, height = map(int, input().split())
        grid: List[List[Optional[Tile]]] = [[None for _ in range(width)] for _ in range(height)]
        blocked: Set[Position] = set()

        for _ in range(height):
            row = input().split()
            for x in range(width):
                tx, ty, ttype = int(row[x*3]), int(row[x*3+1]), int(row[x*3+2])
                grid[ty][tx] = Tile((tx, ty), ttype)
                if ttype != 0:                    
                    blocked.add( Position(tx, ty) )


        state = GameState(my_id, width, height, grid, blocked, agents_meta)

        return state

    def read_turn(self):
        self.my_agents.clear()
        self.enemies.clear()

        agent_count = int(input())
        for _ in range(agent_count):
            agent_id, x, y, cd, splash, wet = map(int, input().split())
            agent = Agent(agent_id, Position(x,y), cd, splash, wet, self.all_agents_meta[ agent_id] )
            if agent.metadata.is_enemy :
                self.enemies.append( agent )
            else:
                self.my_agents.append( agent )


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
    def compute_expected_damage(
        self,
        shooter: Agent,
        from_tile: Position,
        target: Agent,
        grid: Grid
    ) -> int:
        dist = from_tile.distance_to(target.position)
        if dist > 2 * shooter.metadata.opt_range:
            return 0

        # Base damage
        if dist <= shooter.metadata.opt_range:
            damage = shooter.metadata.soak_power
        else:
            damage = shooter.metadata.soak_power // 2

        # Check all adjacent tiles around the target
        max_cover = 0  # 0 = no cover, 50 = low, 75 = high
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            cx = target.position.x + dx
            cy = target.position.y + dy
            if 0 <= cx < len(grid[0]) and 0 <= cy < len(grid):
                tile = grid[cy][cx]
                if tile.tile_type in (1, 2):
                    # Check if shooter is *not* also adjacent to this cover
                    if abs(from_tile.x - cx) + abs(from_tile.y - cy) > 1:
                        if tile.tile_type == 2:
                            max_cover = max(max_cover, 75)
                        elif tile.tile_type == 1:
                            max_cover = max(max_cover, 50)

        # Apply cover penalty if any
        damage = damage * (100 - max_cover) // 100
        return damage

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
                cmds.append(f"MOVE {move_tile.x} {move_tile.y}")
                blocked.add( move_tile )
            else:
                blocked.add( agent.position )


            # Find best enemy to shoot from this tile
            best_target:Agent = None
            max_damage = 0
            for enemy in state.enemies:
                dmg = self.compute_expected_damage(agent, move_tile, enemy, state.grid)
                if dmg > max_damage:
                    best_target = enemy
                    max_damage = dmg

            if agent.cooldown == 0 and best_target and max_damage > 0:
                cmds.append(f"SHOOT {best_target.agent_id}")

            if not cmds:
                cmds = ["HUNKER_DOWN"]

            actions.append(f"{agent.agent_id};{';'.join(cmds)}")
            print(f"DEBUG: {agent.agent_id};{';'.join(cmds)}", file=sys.stderr)
            
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
