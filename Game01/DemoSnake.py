import random
import sys
from dataclasses import dataclass

import pygame


COLS = 10
ROWS = 20
CELL = 30
BOARD_WIDTH = COLS * CELL
BOARD_HEIGHT = ROWS * CELL
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 700

BACKGROUND = (245, 240, 232)
INK = (23, 32, 38)
BOARD_COLOR = (32, 43, 49)
PANEL_COLOR = (255, 250, 241)
MUTED = (101, 114, 120)
CORAL = (231, 91, 69)
TEAL = (19, 138, 139)
YELLOW = (240, 186, 67)

PIECES = (
    ([[1, 1, 1, 1]], (39, 184, 197)),
    ([[1, 1], [1, 1]], YELLOW),
    ([[0, 1, 0], [1, 1, 1]], (168, 121, 213)),
    ([[1, 0, 0], [1, 1, 1]], (232, 139, 67)),
    ([[0, 0, 1], [1, 1, 1]], (78, 127, 209)),
    ([[0, 1, 1], [1, 1, 0]], (99, 189, 115)),
    ([[1, 1, 0], [0, 1, 1]], (223, 99, 127)),
)


@dataclass
class Piece:
    shape: list[list[int]]
    color: tuple[int, int, int]
    x: int = 0
    y: int = 0


def new_board() -> list[list[tuple[int, int, int] | None]]:
    return [[None for _ in range(COLS)] for _ in range(ROWS)]


def random_piece() -> Piece:
    shape, color = random.choice(PIECES)
    return Piece([row[:] for row in shape], color)


def reset_piece(piece: Piece) -> None:
    piece.x = COLS // 2 - len(piece.shape[0]) // 2
    piece.y = 0


def rotate(matrix: list[list[int]]) -> list[list[int]]:
    return [list(row) for row in zip(*matrix[::-1])]


def collides(board: list[list[tuple[int, int, int] | None]], piece: Piece) -> bool:
    for row_index, row in enumerate(piece.shape):
        for column_index, value in enumerate(row):
            if not value:
                continue
            x = piece.x + column_index
            y = piece.y + row_index
            if x < 0 or x >= COLS or y >= ROWS:
                return True
            if y >= 0 and board[y][x] is not None:
                return True
    return False


def draw_cell(surface: pygame.Surface, x: int, y: int, color: tuple[int, int, int], size: int = CELL) -> None:
    rectangle = pygame.Rect(x * size, y * size, size, size)
    pygame.draw.rect(surface, color, rectangle)
    pygame.draw.rect(surface, (55, 68, 72), rectangle, 2)
    pygame.draw.rect(surface, (255, 255, 255, 45), (rectangle.x + 4, rectangle.y + 4, size - 12, 4))


def draw_piece(surface: pygame.Surface, piece: Piece, size: int = CELL, offset: tuple[int, int] = (0, 0)) -> None:
    for row_index, row in enumerate(piece.shape):
        for column_index, value in enumerate(row):
            if value:
                draw_cell(surface, column_index + piece.x + offset[0], row_index + piece.y + offset[1], piece.color, size)


def draw_board(surface: pygame.Surface, board: list[list[tuple[int, int, int] | None]], piece: Piece) -> None:
    surface.fill(BOARD_COLOR)
    for x in range(COLS + 1):
        pygame.draw.line(surface, (49, 62, 67), (x * CELL, 0), (x * CELL, BOARD_HEIGHT))
    for y in range(ROWS + 1):
        pygame.draw.line(surface, (49, 62, 67), (0, y * CELL), (BOARD_WIDTH, y * CELL))
    for y, row in enumerate(board):
        for x, color in enumerate(row):
            if color:
                draw_cell(surface, x, y, color)
    draw_piece(surface, piece)


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str, position: tuple[int, int], color: tuple[int, int, int] = INK) -> None:
    surface.blit(font.render(text, True, color), position)


def draw_panel(surface: pygame.Surface, title_font: pygame.font.Font, body_font: pygame.font.Font, title: str, rectangle: pygame.Rect) -> None:
    pygame.draw.rect(surface, PANEL_COLOR, rectangle)
    pygame.draw.rect(surface, INK, rectangle, 2)
    draw_text(surface, title_font, title, (rectangle.x + 16, rectangle.y + 14), TEAL)


def draw_next(surface: pygame.Surface, piece: Piece, rectangle: pygame.Rect) -> None:
    preview = pygame.Surface(rectangle.size)
    preview.fill((240, 234, 223))
    preview_piece = Piece(piece.shape, piece.color)
    preview_piece.x = (4 - len(piece.shape[0])) // 2
    preview_piece.y = (4 - len(piece.shape)) // 2
    draw_piece(preview, preview_piece, 24)
    surface.blit(preview, rectangle.topleft)


def merge(board: list[list[tuple[int, int, int] | None]], piece: Piece) -> None:
    for row_index, row in enumerate(piece.shape):
        for column_index, value in enumerate(row):
            if value and piece.y + row_index >= 0:
                board[piece.y + row_index][piece.x + column_index] = piece.color


def clear_lines(board: list[list[tuple[int, int, int] | None]]) -> tuple[list[list[tuple[int, int, int] | None]], int]:
    remaining = [row for row in board if not all(row)]
    cleared = ROWS - len(remaining)
    return [[None for _ in range(COLS)] for _ in range(cleared)] + remaining, cleared


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Blockfall - Python Tetris")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    board_surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
    title_font = pygame.font.Font(None, 58)
    section_font = pygame.font.Font(None, 22)
    body_font = pygame.font.Font(None, 24)
    small_font = pygame.font.Font(None, 19)
    clock = pygame.time.Clock()

    board = new_board()
    current_piece = random_piece()
    next_piece = random_piece()
    reset_piece(current_piece)
    score = 0
    lines = 0
    level = 1
    drop_timer = 0
    paused = False
    game_over = False
    running = True

    while running:
        elapsed = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_r:
                board = new_board()
                current_piece = random_piece()
                next_piece = random_piece()
                reset_piece(current_piece)
                score = lines = 0
                level = 1
                drop_timer = 0
                paused = game_over = False
            elif event.key == pygame.K_p and not game_over:
                paused = not paused
            elif not paused and not game_over:
                if event.key == pygame.K_LEFT:
                    current_piece.x -= 1
                    if collides(board, current_piece):
                        current_piece.x += 1
                elif event.key == pygame.K_RIGHT:
                    current_piece.x += 1
                    if collides(board, current_piece):
                        current_piece.x -= 1
                elif event.key == pygame.K_UP:
                    previous_shape = current_piece.shape
                    current_piece.shape = rotate(current_piece.shape)
                    if collides(board, current_piece):
                        current_piece.shape = previous_shape
                elif event.key == pygame.K_SPACE:
                    while not collides(board, current_piece):
                        current_piece.y += 1
                    current_piece.y -= 1
                    drop_timer = 1000
                elif event.key == pygame.K_DOWN:
                    drop_timer = 1000

        if not paused and not game_over:
            drop_timer += elapsed
            interval = max(100, 800 - (level - 1) * 65)
            if drop_timer >= interval:
                drop_timer = 0
                current_piece.y += 1
                if collides(board, current_piece):
                    current_piece.y -= 1
                    merge(board, current_piece)
                    board, cleared = clear_lines(board)
                    if cleared:
                        lines += cleared
                        score += (0, 100, 300, 500, 800)[cleared] * level
                        level = lines // 10 + 1
                    current_piece = next_piece
                    next_piece = random_piece()
                    reset_piece(current_piece)
                    if collides(board, current_piece):
                        game_over = True

        screen.fill(BACKGROUND)
        draw_text(screen, title_font, "BLOCKFALL", (45, 36))
        draw_text(screen, small_font, "PYGAME / PYTHON", (48, 88), TEAL)
        draw_board(board_surface, board, current_piece)
        screen.blit(board_surface, (45, 125))

        score_panel = pygame.Rect(390, 125, 260, 145)
        next_panel = pygame.Rect(390, 287, 260, 185)
        controls_panel = pygame.Rect(390, 489, 260, 130)
        draw_panel(screen, section_font, body_font, "SCORE", score_panel)
        draw_text(screen, title_font, f"{score:,}", (score_panel.x + 16, score_panel.y + 38))
        draw_text(screen, small_font, f"LINES     {lines}", (score_panel.x + 16, score_panel.y + 103), MUTED)
        draw_text(screen, small_font, f"LEVEL     {level}", (score_panel.x + 136, score_panel.y + 103), MUTED)
        draw_panel(screen, section_font, body_font, "NEXT BLOCK", next_panel)
        draw_next(screen, next_piece, pygame.Rect(next_panel.x + 16, next_panel.y + 43, 120, 120))
        draw_panel(screen, section_font, body_font, "CONTROLS", controls_panel)
        draw_text(screen, small_font, "ARROWS  MOVE / ROTATE", (controls_panel.x + 16, controls_panel.y + 42), MUTED)
        draw_text(screen, small_font, "SPACE   HARD DROP", (controls_panel.x + 16, controls_panel.y + 67), MUTED)
        draw_text(screen, small_font, "P       PAUSE    R  NEW GAME", (controls_panel.x + 16, controls_panel.y + 92), MUTED)

        if paused or game_over:
            overlay = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
            overlay.fill((23, 32, 38, 225))
            board_surface.blit(overlay, (0, 0))
            message = "GAME OVER" if game_over else "PAUSED"
            draw_text(board_surface, title_font, message, (36, 245), (255, 255, 255))
            draw_text(board_surface, small_font, "PRESS R TO RESTART" if game_over else "PRESS P TO CONTINUE", (52, 310), (215, 223, 221))
            screen.blit(board_surface, (45, 125))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()