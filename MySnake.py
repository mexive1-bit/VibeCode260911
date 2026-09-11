import math
import random
import sys
from dataclasses import dataclass, field

import pygame


GRID_WIDTH = 30
GRID_HEIGHT = 22
CELL_SIZE = 26
BOARD_WIDTH = GRID_WIDTH * CELL_SIZE
BOARD_HEIGHT = GRID_HEIGHT * CELL_SIZE
PANEL_WIDTH = 250
WINDOW_WIDTH = BOARD_WIDTH + PANEL_WIDTH
WINDOW_HEIGHT = BOARD_HEIGHT
SNAKE_COUNT = 3
STARTING_LENGTH = 4
FOOD_COUNT = 24
ITEM_COUNT = 7
FPS = 60

BACKGROUND = (13, 20, 27)
BOARD_COLOR = (20, 31, 38)
GRID_COLOR = (28, 44, 50)
TEXT = (235, 242, 238)
MUTED = (142, 165, 166)
FOOD_COLOR = (247, 105, 91)
ITEM_COLORS = {"speed": (247, 191, 68), "shield": (86, 186, 239), "cloak": (190, 127, 230)}
SNAKE_COLORS = [
    (66, 211, 161), (242, 109, 92), (244, 180, 67), (103, 164, 245),
    (219, 117, 185), (133, 209, 101), (239, 137, 64), (102, 194, 199),
    (190, 155, 242), (231, 220, 100),
]
DIRECTIONS = [(1, 0), (0, 1), (-1, 0), (0, -1)]
ITEM_NAMES = {"speed": "SPEED", "shield": "SHIELD", "cloak": "CLOAK"}


@dataclass
class Item:
    position: tuple[int, int]
    kind: str


@dataclass
class Snake:
    snake_id: int
    name: str
    color: tuple[int, int, int]
    body: list[tuple[int, int]]
    direction: tuple[int, int]
    is_player: bool = False
    score: int = 0
    move_timer: float = 0.0
    speed_until: float = 0.0
    shield_until: float = 0.0
    cloak_until: float = 0.0
    alive: bool = True
    target: tuple[int, int] | None = None

    @property
    def head(self) -> tuple[int, int]:
        return self.body[0]

    @property
    def length(self) -> int:
        return len(self.body)

    def has_effect(self, effect: str, now: float) -> bool:
        return getattr(self, f"{effect}_until") > now

    def step_interval(self, now: float) -> float:
        return 0.15 if self.has_effect("speed", now) else 0.27


def random_empty_position(snakes: list[Snake], foods: list[tuple[int, int]], items: list[Item]) -> tuple[int, int]:
    occupied = {part for snake in snakes if snake.alive for part in snake.body}
    occupied.update(foods)
    occupied.update(item.position for item in items)
    for _ in range(200):
        position = (random.randrange(GRID_WIDTH), random.randrange(GRID_HEIGHT))
        if position not in occupied:
            return position
    return (random.randrange(GRID_WIDTH), random.randrange(GRID_HEIGHT))


def create_snakes() -> list[Snake]:
    snakes: list[Snake] = []
    starts = [(3, 3), (26, 3), (3, 18)][:SNAKE_COUNT]
    for snake_id, (x, y) in enumerate(starts):
        direction = (1, 0) if x < GRID_WIDTH // 2 else (-1, 0)
        body = [(x - direction[0] * index, y - direction[1] * index) for index in range(STARTING_LENGTH)]
        snakes.append(Snake(snake_id, "YOU" if snake_id == 0 else f"BOT {snake_id}", SNAKE_COLORS[snake_id], body, direction, snake_id == 0))
    return snakes


def spawn_world(snakes: list[Snake]) -> tuple[list[tuple[int, int]], list[Item]]:
    foods: list[tuple[int, int]] = []
    items: list[Item] = []
    for _ in range(FOOD_COUNT):
        foods.append(random_empty_position(snakes, foods, items))
    for _ in range(ITEM_COUNT):
        kind = random.choice(list(ITEM_COLORS))
        items.append(Item(random_empty_position(snakes, foods, items), kind))
    return foods, items


def inside(position: tuple[int, int]) -> bool:
    return 0 <= position[0] < GRID_WIDTH and 0 <= position[1] < GRID_HEIGHT


def distance(first: tuple[int, int], second: tuple[int, int]) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def choose_ai_direction(snake: Snake, snakes: list[Snake], foods: list[tuple[int, int]], items: list[Item], now: float) -> None:
    head = snake.head
    if snake.target is None or distance(head, snake.target) < 2 or random.random() < 0.035:
        choices = foods + [item.position for item in items]
        snake.target = min(choices, key=lambda position: distance(head, position)) if choices else None

    candidates = list(DIRECTIONS)
    reverse = (-snake.direction[0], -snake.direction[1])
    if snake.length > 1 and reverse in candidates:
        candidates.remove(reverse)
    safe: list[tuple[int, int]] = []
    occupied = {part for other in snakes if other.alive for part in other.body[1:]}
    for direction in candidates:
        next_position = (head[0] + direction[0], head[1] + direction[1])
        if inside(next_position) and next_position not in occupied:
            safe.append(direction)
    if not safe:
        return
    if snake.target:
        snake.direction = min(safe, key=lambda direction: distance((head[0] + direction[0], head[1] + direction[1]), snake.target))
    elif random.random() < 0.15:
        snake.direction = random.choice(safe)


def remove_snake(snake: Snake, reason: str, messages: list[str]) -> None:
    snake.alive = False
    messages.append(f"{snake.name} {reason}")


def apply_item(snake: Snake, item: Item, now: float, messages: list[str]) -> None:
    if item.kind == "speed":
        snake.speed_until = max(snake.speed_until, now) + 7.0
    elif item.kind == "shield":
        snake.shield_until = max(snake.shield_until, now) + 6.0
    else:
        snake.cloak_until = max(snake.cloak_until, now) + 6.0
    messages.append(f"{snake.name} got {ITEM_NAMES[item.kind]}")


def move_snake(snake: Snake, snakes: list[Snake], foods: list[tuple[int, int]], items: list[Item], now: float, messages: list[str]) -> None:
    if not snake.alive:
        return
    if not snake.is_player:
        choose_ai_direction(snake, snakes, foods, items, now)
    new_head = (snake.head[0] + snake.direction[0], snake.head[1] + snake.direction[1])
    snake.move_timer = 0
    if not inside(new_head):
        if snake.has_effect("shield", now):
            snake.direction = (-snake.direction[0], -snake.direction[1])
            return
        remove_snake(snake, "hit the wall", messages)
        return
    snake.body.insert(0, new_head)
    ate_food = new_head in foods
    if ate_food:
        foods.remove(new_head)
        snake.score += 1
    else:
        snake.body.pop()
    for item in items[:]:
        if item.position == new_head:
            apply_item(snake, item, now, messages)
            items.remove(item)
    if not ate_food and random.random() < 0.08 and len(foods) < FOOD_COUNT:
        foods.append(random_empty_position(snakes, foods, items))


def resolve_collisions(snakes: list[Snake], now: float, messages: list[str]) -> None:
    alive = [snake for snake in snakes if snake.alive]
    for snake in alive:
        if not snake.alive:
            continue
        for other in alive:
            if snake is other or not other.alive or snake.head not in other.body:
                continue
            if snake.head == other.head:
                if snake.has_effect("shield", now):
                    remove_snake(other, f"lost to {snake.name}", messages)
                elif other.has_effect("shield", now):
                    remove_snake(snake, f"lost to {other.name}", messages)
                elif snake.score > other.score:
                    remove_snake(other, f"was eaten by {snake.name}", messages)
                elif other.score > snake.score:
                    remove_snake(snake, f"was eaten by {other.name}", messages)
                else:
                    remove_snake(snake, "lost a tied duel", messages)
                continue
            if snake.head in other.body[1:]:
                if snake.has_effect("shield", now) or snake.score > other.score:
                    remove_snake(other, f"was eaten by {snake.name}", messages)
                elif not snake.has_effect("cloak", now):
                    remove_snake(snake, f"hit {other.name}", messages)


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str, position: tuple[int, int], color: tuple[int, int, int] = TEXT) -> None:
    surface.blit(font.render(text, True, color), position)


def draw_game(screen: pygame.Surface, snakes: list[Snake], foods: list[tuple[int, int]], items: list[Item], now: float, fonts: dict[str, pygame.font.Font], messages: list[str], started: bool, paused: bool, winner: Snake | None) -> None:
    screen.fill(BACKGROUND)
    board = pygame.Rect(0, 0, BOARD_WIDTH, BOARD_HEIGHT)
    pygame.draw.rect(screen, BOARD_COLOR, board)
    for x in range(0, BOARD_WIDTH + 1, CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, BOARD_HEIGHT))
    for y in range(0, BOARD_HEIGHT + 1, CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (BOARD_WIDTH, y))
    for food in foods:
        center = (food[0] * CELL_SIZE + CELL_SIZE // 2, food[1] * CELL_SIZE + CELL_SIZE // 2)
        pygame.draw.circle(screen, FOOD_COLOR, center, CELL_SIZE // 4)
    for item in items:
        rectangle = pygame.Rect(item.position[0] * CELL_SIZE + 5, item.position[1] * CELL_SIZE + 5, CELL_SIZE - 10, CELL_SIZE - 10)
        pygame.draw.rect(screen, ITEM_COLORS[item.kind], rectangle, border_radius=5)
        draw_text(screen, fonts["tiny"], item.kind[0].upper(), (rectangle.x + 6, rectangle.y + 3), BACKGROUND)
    for snake in snakes:
        if not snake.alive or snake.has_effect("cloak", now):
            continue
        for index, part in enumerate(reversed(snake.body)):
            rectangle = pygame.Rect(part[0] * CELL_SIZE + 2, part[1] * CELL_SIZE + 2, CELL_SIZE - 4, CELL_SIZE - 4)
            if snake.is_player:
                pulse = (math.sin(now * 8.0) + 1.0) / 2.0
                color = tuple(min(255, int(channel + (255 - channel) * 0.45 * pulse)) for channel in snake.color)
            else:
                color = tuple(max(0, channel - 30) for channel in snake.color) if index else snake.color
            pygame.draw.rect(screen, color, rectangle, border_radius=7)
            if snake.is_player:
                glow = 2 + int((math.sin(now * 8.0) + 1.0) * 2)
                pygame.draw.rect(screen, (245, 255, 220), rectangle.inflate(glow, glow), 1, border_radius=8)
        head = pygame.Rect(snake.head[0] * CELL_SIZE + 2, snake.head[1] * CELL_SIZE + 2, CELL_SIZE - 4, CELL_SIZE - 4)
        if snake.has_effect("shield", now):
            pygame.draw.rect(screen, (170, 230, 255), head.inflate(5, 5), 2, border_radius=9)
        pygame.draw.circle(screen, BACKGROUND, (head.x + 9, head.y + 9), 2)
        pygame.draw.circle(screen, BACKGROUND, (head.x + 17, head.y + 9), 2)
    panel = pygame.Rect(BOARD_WIDTH, 0, PANEL_WIDTH, WINDOW_HEIGHT)
    pygame.draw.rect(screen, (16, 26, 32), panel)
    draw_text(screen, fonts["title"], "MY SNAKE", (BOARD_WIDTH + 18, 22), SNAKE_COLORS[0])
    draw_text(screen, fonts["small"], "3 SNAKES / LAST ONE WINS", (BOARD_WIDTH + 18, 59), MUTED)
    alive = sorted((snake for snake in snakes if snake.alive), key=lambda snake: (-snake.score, -snake.length))
    draw_text(screen, fonts["section"], f"SURVIVORS  {len(alive)}", (BOARD_WIDTH + 18, 96), TEXT)
    for index, snake in enumerate(alive):
        y = 128 + index * 28
        pygame.draw.rect(screen, snake.color, (BOARD_WIDTH + 18, y + 4, 12, 12), border_radius=3)
        draw_text(screen, fonts["small"], f"{index + 1:>2}  {snake.name:<5} {snake.score:>2} pts", (BOARD_WIDTH + 38, y), TEXT if snake.is_player else MUTED)
    draw_text(screen, fonts["section"], "ITEMS", (BOARD_WIDTH + 18, 420), TEXT)
    draw_text(screen, fonts["small"], "S  SPEED   H  SHIELD", (BOARD_WIDTH + 18, 450), ITEM_COLORS["speed"])
    draw_text(screen, fonts["small"], "C  CLOAK", (BOARD_WIDTH + 18, 476), ITEM_COLORS["cloak"])
    draw_text(screen, fonts["section"], "CONTROLS", (BOARD_WIDTH + 18, 530), TEXT)
    draw_text(screen, fonts["small"], "ARROWS / WASD  MOVE", (BOARD_WIDTH + 18, 560), MUTED)
    draw_text(screen, fonts["small"], "P  PAUSE    R  RESTART", (BOARD_WIDTH + 18, 586), MUTED)
    if messages:
        draw_text(screen, fonts["tiny"], messages[-1][:30], (BOARD_WIDTH + 18, 650), MUTED)
    if not started or paused or winner:
        overlay = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 14, 200))
        screen.blit(overlay, (0, 0))
        title = f"{winner.name} WINS!" if winner else ("MY SNAKE" if not started else "PAUSED")
        draw_text(screen, fonts["title"], title, (BOARD_WIDTH // 2 - 115, BOARD_HEIGHT // 2 - 40), winner.color if winner else TEXT)
        prompt = "PRESS ENTER OR SPACE TO START" if not started else ("PRESS R TO PLAY AGAIN" if winner else "PRESS P TO CONTINUE")
        draw_text(screen, fonts["small"], prompt, (BOARD_WIDTH // 2 - 102, BOARD_HEIGHT // 2 + 12), TEXT)


def reset_game() -> tuple[list[Snake], list[tuple[int, int]], list[Item]]:
    snakes = create_snakes()
    foods, items = spawn_world(snakes)
    return snakes, foods, items


def main() -> None:
    pygame.init()
    pygame.display.set_caption("My Snake - 10 Snake Arena")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    fonts = {"title": pygame.font.Font(None, 34), "section": pygame.font.Font(None, 22), "small": pygame.font.Font(None, 18), "tiny": pygame.font.Font(None, 15)}
    snakes, foods, items = reset_game()
    messages: list[str] = []
    started = False
    paused = False
    winner: Snake | None = None
    running = True
    elapsed_total = 0.0
    while running:
        elapsed = clock.tick(FPS) / 1000.0
        elapsed_total += elapsed
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and not winner:
                    started = True
                elif event.key == pygame.K_r:
                    snakes, foods, items = reset_game()
                    messages.clear()
                    started = False
                    winner = None
                    paused = False
                elif event.key == pygame.K_p and started and not winner:
                    paused = not paused
                elif started and event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s, pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                    player = snakes[0]
                    key_directions = {pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0)}
                    new_direction = key_directions[event.key]
                    if new_direction != (-player.direction[0], -player.direction[1]):
                        player.direction = new_direction
        if started and not paused and not winner:
            for snake in snakes:
                if snake.alive:
                    snake.move_timer += elapsed
                    if snake.move_timer >= snake.step_interval(elapsed_total):
                        move_snake(snake, snakes, foods, items, elapsed_total, messages)
            resolve_collisions(snakes, elapsed_total, messages)
            while len(foods) < FOOD_COUNT:
                foods.append(random_empty_position(snakes, foods, items))
            alive = [snake for snake in snakes if snake.alive]
            if len(alive) == 1:
                winner = alive[0]
            elif not snakes[0].alive and len(alive) == 0:
                winner = max(snakes, key=lambda snake: snake.score)
        draw_game(screen, snakes, foods, items, elapsed_total, fonts, messages, started, paused, winner)
        pygame.display.flip()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()