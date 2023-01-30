import random
from time import perf_counter
import pygame
import copy
import neat
from enum import Enum
from dataclasses import dataclass

WINDOW_WIDTH, WINDOW_HEIGHT = 640, 640
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
LIGHTGRAY = (150, 150, 150)

WINDOW = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Tetris")

UPDATE = pygame.USEREVENT + 1

pygame.time.set_timer(UPDATE, 100)

@dataclass
class Pair:
    x: int
    y: int

    def __add__(self, val: int):
        self.x += val
        self.y += val

@dataclass
class Color:
    r: int
    g: int
    b: int

    def value(self) -> tuple[int]:
        return (self.r, self.g, self.b)

@dataclass
class BlockFormat:
    block: list[list[int]]
    color: Color

class Direction(Enum):
    Up=0
    Down=1
    Left=2
    Right=3

BLOCKTYPES = {
    "IBlock": BlockFormat([
            (0, 0, 0, 0),
            (0, 0, 0, 0),
            (1, 1, 1, 1),
            (0, 0, 0, 0),
        ], Color(0, 240, 240)),
    "JBlock": BlockFormat([
            (0, 0, 0, 0),
            (0, 1, 0, 0),
            (0, 1, 1, 1),
            (0, 0, 0, 0),
        ], Color(0, 0, 240)),
    "LBlock": BlockFormat([
            (0, 0, 0, 0),
            (0, 0, 1, 0),
            (1, 1, 1, 0),
            (0, 0, 0, 0),
        ], Color(240, 160, 0)),
    "OBlock": BlockFormat([
            (0, 0, 0, 0),
            (0, 1, 1, 0),
            (0, 1, 1, 0),
            (0, 0, 0, 0),
        ], Color(240, 240, 0)),
    "SBlock": BlockFormat([
            (0, 0, 0, 0),
            (0, 1, 1, 0),
            (1, 1, 0, 0),
            (0, 0, 0, 0),
        ], Color(0, 240, 0)),
    "TBlock": BlockFormat([
            (0, 0, 0, 0),
            (0, 1, 0, 0),
            (1, 1, 1, 0),
            (0, 0, 0, 0),
        ], Color(160, 0, 240)),
    "ZBlock": BlockFormat([
            (0, 0, 0, 0),
            (0, 1, 1, 0),
            (0, 0, 1, 1),
            (0, 0, 0, 0),
        ], Color(240, 0, 0)),
}

BLOCKINDICES = [
    "IBlock",
    "JBlock",
    "LBlock",
    "OBlock",
    "SBlock",
    "TBlock",
    "ZBlock"
]

class Square:
    WIDTH = 32
    HEIGHT = 32

    squares = []

    def __init__(self, position: Pair, color: Color) -> None: 
        self.position = position
        self.color = color
        Square.squares.append(self)

    def render(self) -> None:
        x = Tetris.XPOS + self.position.x * Square.WIDTH
        y = Tetris.YPOS + self.position.y * Square.HEIGHT
        rect = pygame.Rect(x, y, Square.WIDTH, Square.HEIGHT)
        pygame.draw.rect(WINDOW, self.color.value(), rect)

class Block:
    @classmethod
    def rotate_matrix(cls, block: list[list[int]]) -> list[list[int]]:
        return list(zip(*block[::-1]))

    @classmethod
    def block_intersect(cls, block: "Block", blocks: list["Block"]) -> bool:
        return any(square.position == s.position for square in block.squares for b in blocks if b is not block for s in b.squares)

    def __init__(self, format_name: str, grid_position: Pair) -> None:
        format = BLOCKTYPES[format_name]
        self.block = copy.deepcopy(format.block)
        self.block_type = BLOCKINDICES.index(format_name)
        self.color = format.color
        self.grid_position = grid_position
        self.squares = [Square(Pair(0, 0), self.color) for _ in range(4)]
        self._update_squares()
        self.rotation = 0
        curr = self.block
        self.rotations = [curr] + [(curr := Block.rotate_matrix(curr)) for _ in range(3)]

    def _update_squares(self) -> bool:
        curr = 0
        for i in range(4):
            for j in range(4):
                if self.block[i][j] == 1:
                    self.squares[curr].position.x = self.grid_position.x + j
                    self.squares[curr].position.y = self.grid_position.y + i
                    if self.squares[curr].position.y >= 20:
                        return False
                    curr += 1
        return True

    def landed(self, blocks: list["Block"]) -> bool:
        return len(self.squares) == 0 or any(square.position.y >= 19 for square in self.squares) or \
                any(s1.position.x == s2.position.x and s1.position.y == s2.position.y + 1 for block in blocks if block is not \
                    self for s1 in block.squares for s2 in self.squares)

    def rotate(self, blocks: list["Block"]) -> None:
        self.rotation -= 1
        if self.rotation < 0: self.rotation = 3
        self.block = self.rotations[self.rotation]
        if not self._update_squares() or Block.block_intersect(self, blocks):
            self.rotation += 1
            if self.rotation > 3: self.rotation = 0
            self.block = self.rotations[self.rotation]
            self._update_squares()
        else:
            self.move([], Direction.Left, 0)
            self.move([], Direction.Right, 0)

    def move(self, blocks: list["Block"], direction: Direction, distance: int = 1) -> None:
        match direction:
            case Direction.Left:
                # find left most block's column
                col = 0
                cols = list(zip(*self.block))
                for i in range(4):
                    if 1 in cols[i]:
                        col = i
                        break
                prevx = self.grid_position.x
                self.grid_position.x = max(self.grid_position.x - distance, -col)
                self._update_squares()
                if Block.block_intersect(self, blocks):
                    self.grid_position.x = prevx
                    self._update_squares()
            case Direction.Right:
                # find right most block's column
                col = 0
                cols = list(zip(*self.block))
                for i in range(3, -1, -1):
                    if 1 in cols[i]:
                        col = i
                        break
                prevx = self.grid_position.x
                self.grid_position.x = min(self.grid_position.x + distance, 9 - col)
                self._update_squares()
                if Block.block_intersect(self, blocks):
                    self.grid_position.x = prevx
                    self._update_squares()
            case Direction.Down:
                self.grid_position.y += distance
                for square in self.squares:
                    square.position.y += distance

    def render(self) -> None:
        for square in self.squares:
            square.render()

class Tetris:
    WIDTH = Square.WIDTH * 10
    HEIGHT = Square.HEIGHT * 20
    XPOS = (WINDOW_WIDTH - WIDTH) / 2
    YPOS = (WINDOW_HEIGHT - HEIGHT) / 2

    def __init__(self, genome):
        self.running = True
        self.genome = genome
        self.blocks = []
        self.active_block = None

    def keypress(self, key: int) -> None:
        # key handling
        if self.active_block is None: return
        if key == pygame.K_UP:
            self.active_block.rotate(self.blocks)
        elif key == pygame.K_LEFT:
            self.active_block.move(self.blocks, Direction.Left)
        elif key == pygame.K_RIGHT:
            self.active_block.move(self.blocks, Direction.Right)

    def update(self) -> None:
        if self.active_block is None:
            # set active block to new block of random type at coordinates 3, -4 on the grid
            self.active_block = Block(random.choice(list(BLOCKTYPES.keys())), Pair(3, -4))
            self.blocks.append(self.active_block)
        else:
            if self.active_block.landed(self.blocks):
                update_blocks = []
                # Checking for line breaks
                for i in range(19, -1, -1):
                    squares = [square for block in self.blocks for square in block.squares if square.position.y == i]
                    if len(squares) == 10:
                        self.genome.fitness += 150
                        for square in squares:
                            for block in self.blocks:
                                if square in block.squares:
                                    block.squares.remove(square)
                                    update_blocks.append(block)
                # updating line break blocks
                for block in self.blocks:
                    if block is self.active_block: continue
                    while not block.landed(self.blocks):
                        block.move(self.blocks, Direction.Down)
                # game over check
                if self.active_block.grid_position.y < 0:
                    self.running = False
                # ready to set new active block
                self.active_block = None
            else:
                self.active_block.move(self.blocks, Direction.Down)
        mhpc = [0 for _ in range(10)]
        for block in self.blocks:
            if block is self.active_block: continue
            for square in block.squares:
                mhpc[square.position.x] = max(mhpc[square.position.x], square.position.y)
        self.bumpiness = sum(abs(mhpc[i] - mhpc[i - 1]) for i in range(1, 10))
        self.aggregate_height = sum(mhpc)

    def render(self) -> None:
        for block in self.blocks:
            block.render()
        for i in range(11):
            x = Tetris.XPOS + i * Square.WIDTH
            pygame.draw.line(WINDOW, LIGHTGRAY, (x, Tetris.YPOS), (x, Tetris.YPOS + Tetris.HEIGHT))
        for i in range(21):
            y = Tetris.YPOS + i * Square.HEIGHT
            pygame.draw.line(WINDOW, LIGHTGRAY, (Tetris.XPOS, y), (Tetris.XPOS + Tetris.WIDTH, y))

def run(genomes: list[list[int]], config: neat.config.Config) -> None:

    nets = []
    ge = []

    for _, g in genomes:
        g.fitness = 0
        ge.append(g)
        nets.append(neat.nn.FeedForwardNetwork.create(g, config))

    running = True
    
    games = [Tetris(ge[i]) for i in range(len(ge))]

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == UPDATE:
                for i, game in enumerate(games):
                    game.update()

                    if not game.running:
                        game.genome.fitness -= 50
                        ge.pop(i)
                        games.pop(i)
                        continue

                    game.genome.fitness += 1 / (0.5 * game.aggregate_height + 0.18 * game.bumpiness + 1)

                    x = [[0 for _ in range(10)] for _ in range(20)]

                    for block in game.blocks:
                        for square in block.squares:
                            try:
                                x[square.position.y - 1][square.position.x] = 2 if block is game.active_block else 1
                            except:
                                pass

                    bt = game.active_block.block_type if game.active_block is not None else -1

                    outputs = nets[i].activate([col for row in x for col in row] + 
                                                [1 if bt == i else 0 for i in range(7)])
                    output = outputs.index(max(outputs))

                    if output == 0:
                        game.keypress(pygame.K_LEFT)
                    elif output == 1:
                        game.keypress(pygame.K_RIGHT)
                    elif output == 2:
                        game.keypress(pygame.K_UP)

        if len(ge) == 0:
            break

        WINDOW.fill(BLACK)
        games[0].render()
        pygame.display.update()

def main() -> None:
    config_path = "./config"
    config = neat.config.Config(
        neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet, neat.DefaultStagnation, config_path
    )

    p = neat.Population(config)

    p.add_reporter(neat.StdOutReporter(True))
    p.add_reporter(neat.StatisticsReporter())

    p.run(run, 250)

if __name__ == "__main__":
    main()