import pygame
import chess
import os
import math
import requests
import csv
from stockfish import Stockfish
from collections import Counter
from gpt4all import GPT4All

# Initialize pygame and stockfish
pygame.init()
stockfish = Stockfish(path=r"C:\Users\joelj\Desktop\Chess Coach\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe")

# Window size
WIDTH, HEIGHT = 640, 640
SQ_SIZE = WIDTH // 8
CAPTURE_SIZE = 30
EVAL_WIDTH = 40
COACH_PANEL_HEIGHT = 100
BOARD_Y_OFFSET = COACH_PANEL_HEIGHT
WIN = pygame.display.set_mode((WIDTH+200+EVAL_WIDTH, HEIGHT + COACH_PANEL_HEIGHT))
pygame.display.set_caption("Chess Coach")

#Animation Variables
animations = []  # list of ongoing animations
ANIM_DURATION = 250  # ms (like chess.com ~0.25s)

# piece values for material balance
_PIECE_VALUE = {"P":1.0, "N":3.0, "B":3.0, "R":5.0, "Q":9.0, "K":0.0} 

#See if piece captured
captured_white = []
captured_black = []

#starts centered
current_normalized = 0.0

# Colors
LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
MENU_BG = (50, 50, 50)
WHITE = (255, 255, 255)

# Load images
PIECES = {}
piece_types = ["wp", "wn", "wb", "wr", "wq", "wk",
               "bp", "bn", "bb", "br", "bq", "bk"]

CAPTURED_IMAGES = {
    "wp": pygame.transform.scale(pygame.image.load("assets/wp.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),
    "wn": pygame.transform.scale(pygame.image.load("assets/wn.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),
    "wb": pygame.transform.scale(pygame.image.load("assets/wb.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),
    "wr": pygame.transform.scale(pygame.image.load("assets/wr.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),
    "wq": pygame.transform.scale(pygame.image.load("assets/wq.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),
    "wk": pygame.transform.scale(pygame.image.load("assets/wk.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),

    "bp": pygame.transform.scale(pygame.image.load("assets/bp.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),
    "bn": pygame.transform.scale(pygame.image.load("assets/bn.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),
    "bb": pygame.transform.scale(pygame.image.load("assets/bb.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),
    "br": pygame.transform.scale(pygame.image.load("assets/br.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),
    "bq": pygame.transform.scale(pygame.image.load("assets/bq.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),
    "bk": pygame.transform.scale(pygame.image.load("assets/bk.png"), (CAPTURE_SIZE, CAPTURE_SIZE)),}

for piece in piece_types:
    PIECES[piece] = pygame.transform.scale(
        pygame.image.load(f"assets/{piece}.png"), (SQ_SIZE, SQ_SIZE)
    )

# Chess board state
board = chess.Board()

# Track clicks
selected_square = None
running = True
clock = pygame.time.Clock()

# Fonts
font = pygame.font.SysFont("Arial", 36)


def draw_text(text, y):
    """Helper to draw centered text on screen."""
    label = font.render(text, True, WHITE)
    rect = label.get_rect(center=(WIDTH // 2, y))
    WIN.blit(label, rect)


def menu_screen():
    """Show menu until player chooses a side."""
    choosing = True
    side = None

    while choosing:
        WIN.fill(MENU_BG)
        draw_text("Choose your side", HEIGHT // 3)
        draw_text("Press W for White", HEIGHT // 2)
        draw_text("Press B for Black", HEIGHT // 2 + 50)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_w:
                    side = chess.WHITE
                    choosing = False
                elif event.key == pygame.K_b:
                    side = chess.BLACK
                    choosing = False

    return side


# Menu first
player_color = menu_screen()

def query_local_gpt4all(prompt: str) -> str:
    setup = "You are a helpful and enouraging chess coach who gives consice and short advices"
    model = GPT4All("gpt4all-falcon-q4_0.gguf")
    content = f"Here is the current analysis by stockfish convert it into a better language for a chess player keep in mind your personality:{prompt}"
    with model.chat_session():
        reply = model.generate(f"{setup}\n{content}",max_tokens=400, temp=0.7)
    return reply


def query_groq_llm(prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Missing GROQ_API_KEY environment variable")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a helpful and encouraging chess coach."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]



def draw_board():
    # Board squares
    for row in range(8):
        for col in range(8):
            color = LIGHT if (row + col) % 2 == 0 else DARK
            pygame.draw.rect(WIN, color, (EVAL_WIDTH + col * SQ_SIZE,
                                          BOARD_Y_OFFSET + row * SQ_SIZE,
                                          SQ_SIZE, SQ_SIZE))

    # Highlight
    if selected_square is not None:
        row = 7 - (selected_square // 8) if player_color == chess.WHITE else selected_square // 8
        col = (selected_square % 8) if player_color == chess.WHITE else 7 - (selected_square % 8)
        pygame.draw.rect(WIN, (255, 255, 0),
                         (EVAL_WIDTH + col * SQ_SIZE, BOARD_Y_OFFSET + row * SQ_SIZE, SQ_SIZE, SQ_SIZE), 4)

    # Build a set of to_squares currently animating to hide destination piece
    hiding_to_squares = {anim["to_square"] for anim in animations}

    # Pieces
    for row in range(8):
        for col in range(8):
            board_row = 7 - row if player_color == chess.WHITE else row
            board_col = col if player_color == chess.WHITE else 7 - col
            square_index = board_row * 8 + board_col

            # Skip drawing if an animation is moving a piece into this square
            if square_index in hiding_to_squares:
                continue

            piece = board.piece_at(square_index)
            if piece:
                piece_str = piece.symbol()
                key = piece_str.lower()
                img_key = ("w" if piece_str.isupper() else "b") + key
                WIN.blit(PIECES[img_key], (EVAL_WIDTH + col * SQ_SIZE,
                                           BOARD_Y_OFFSET + row * SQ_SIZE))


def normalize_piece_key(p):
    if len(p) == 1:  # raw like 'N', 'p'
        return ('w' if p.isupper() else 'b') + p.lower()
    return p  # already in 'wp', 'bn' form
    
def draw_captured_pieces():
    # Clear the right panel area before re-drawing captures
    pygame.draw.rect(WIN, (0,0,0), (0 , 0, EVAL_WIDTH, HEIGHT))
    piece_order = {"p": 1, "n": 2, "b": 3, "r": 4, "q": 5, "k": 6}

    norm_white = [normalize_piece_key(p) for p in captured_white]
    norm_black = [normalize_piece_key(p) for p in captured_black]

    sorted_white = sorted(norm_white, key=lambda p: piece_order[p[-1].lower()])
    sorted_black = sorted(norm_black, key=lambda p: piece_order[p[-1].lower()])

    per_row = 4  # pieces per row in the panel
    panel_x = EVAL_WIDTH + WIDTH + 20

    # White captures (top-right)
    for i, piece_key in enumerate(sorted_white):
        row = i // per_row
        col = i % per_row
        x = panel_x + col * (CAPTURE_SIZE + 5)
        y = 20 + row * (CAPTURE_SIZE + 5) + BOARD_Y_OFFSET
        piece_key = piece_key.lower()
        WIN.blit(CAPTURED_IMAGES[piece_key], (x, y))

    # Black captures (bottom-right)
    start_y = HEIGHT // 2 + 20  # start halfway down the panel
    for i, piece_key in enumerate(sorted_black):
        row = i // per_row
        col = i % per_row
        x = panel_x + col * (CAPTURE_SIZE + 5)
        y = start_y + row * (CAPTURE_SIZE + 5) + BOARD_Y_OFFSET
        piece_key = piece_key.lower()
        WIN.blit(CAPTURED_IMAGES[piece_key], (x, y))


def get_square_from_mouse(pos):
    """Convert mouse pos → chess square index considering orientation."""
    x, y = pos
    y -= BOARD_Y_OFFSET  # shift clicks down

    col = (x - EVAL_WIDTH) // SQ_SIZE
    row = y // SQ_SIZE

    if col < 0 or col >= 8 or row < 0 or row >= 8:
        return None  

    if player_color == chess.WHITE:
        board_row = 7 - row
        board_col = col
    else:
        board_row = row
        board_col = 7 - col

    return board_row * 8 + board_col

def start_piece_animation(piece, from_square, to_square):
    """Initialize animation for a moving piece and remember its board squares."""
    if piece is None:
        return

    from_row, from_col = divmod(from_square, 8)
    to_row, to_col = divmod(to_square, 8)

    # Adjust for board orientation
    if player_color == chess.WHITE:
        from_row = 7 - from_row
        to_row = 7 - to_row
    else:
        from_col = 7 - from_col
        to_col = 7 - to_col

    start_x = EVAL_WIDTH + from_col * SQ_SIZE
    start_y = BOARD_Y_OFFSET + from_row * SQ_SIZE
    end_x = EVAL_WIDTH + to_col * SQ_SIZE
    end_y = BOARD_Y_OFFSET + to_row * SQ_SIZE

    piece_key = ('w' if piece.color == chess.WHITE else 'b') + piece.symbol().lower()

    animations.append({
        "piece": piece_key,
        "start": (start_x, start_y),
        "end": (end_x, end_y),
        "from_square": from_square,
        "to_square": to_square,
        "start_time": pygame.time.get_ticks()
    })

def update_piece_animations():
    now = pygame.time.get_ticks()
    finished = []
    for anim in animations:
        elapsed = now - anim["start_time"]
        t = min(1, elapsed / ANIM_DURATION)

        x = anim["start"][0] + (anim["end"][0] - anim["start"][0]) * t
        y = anim["start"][1] + (anim["end"][1] - anim["start"][1]) * t

        WIN.blit(PIECES[anim["piece"]], (x, y))

        if t >= 1:
            finished.append(anim)

    for anim in finished:
        animations.remove(anim)

def ai_move():
    global board
    stockfish.set_fen_position(board.fen())
    result = stockfish.get_best_move()
    if result:
        move = chess.Move.from_uci(result)

        # --- Capture check for AI moves ---
        captured_piece = board.piece_at(move.to_square)
        if captured_piece:
            if captured_piece.color == chess.WHITE:
                captured_white.append(captured_piece.symbol().upper())
            else:
                captured_black.append(captured_piece.symbol().lower())

        if move in board.legal_moves:
            moving_piece = board.piece_at(move.from_square)
            board.push(move)
            start_piece_animation(moving_piece, move.from_square, move.to_square)
            stockfish.set_fen_position(board.fen())
            #Update the eval bar
            evaluation = stockfish.get_evaluation()
            draw_eval_bar(evaluation, player_color)
        else:
            print(f"Stockfish suggested Illegal move{move}")

def draw_eval_bar(evaluation, player_color):
    global current_normalized
    state = evaluation.get("type")
    value = evaluation.get("value")
    if state == "cp":
        eval_cp = value / 100.0
    elif state == "mate":
        # Map mate to large magnitude for bar scaling
        eval_cp = 100.0 if value > 0 else -100.0
    else:
        eval_cp = 0.0
        # Flip to player perspective
    sign = 1 if player_color == chess.WHITE else -1
    player_eval_cp = eval_cp * sign
    # Text from player perspective
    if state == "cp":
        eval_str = f"{player_eval_cp:+.1f}"
    elif state == "mate":
        mate_val = value * sign
        eval_str = f"M{abs(mate_val)}"
    else:
        eval_str = "0.0"

    # Smooth normalization and draw
    target_normalized = math.tanh(player_eval_cp / 10.0)
    alpha = 0.1
    current_normalized = (1 - alpha) * current_normalized + alpha * target_normalized
    bar_height = int((current_normalized + 1) / 2 * HEIGHT)
    pygame.draw.rect(WIN, (0, 0, 0), (0, 0, EVAL_WIDTH, HEIGHT + BOARD_Y_OFFSET))
    pygame.draw.rect(WIN, (0, 0, 0), (0, BOARD_Y_OFFSET, EVAL_WIDTH, HEIGHT - bar_height))
    pygame.draw.rect(WIN, (255, 255, 255), (0, BOARD_Y_OFFSET + (HEIGHT - bar_height), EVAL_WIDTH, bar_height))
    font = pygame.font.SysFont("Bauhaus 93", 10, bold=False)
    text_surface = font.render(eval_str, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(EVAL_WIDTH // 2, BOARD_Y_OFFSET + HEIGHT - 15))
    pygame.draw.rect(WIN, (0, 0, 0), text_rect.inflate(6, 4))
    WIN.blit(text_surface, text_rect)

if player_color == chess.BLACK and board.turn == chess.WHITE:
    ai_move()

def ai_scan():
    result = stockfish.get_best_move()
    top_3 = stockfish.get_top_moves(3)
    evaluation = stockfish.get_evaluation()
    
    # Extract info safely
    state = evaluation.get("type")    # "cp" (centipawns) or "mate"
    points = evaluation.get("value")  # number, e.g., 34 or 3
    
    return state, points, result, top_3

def load_openings_with_stats(openings_file, stats_file):
    openings = {}

    # Load the openings file (screenshot one)
    with open(openings_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            eco = row["eco"]
            openings[eco] = {
                "eco": eco,
                "name": row["name"],
                "uci": row["uci"].strip(),
                "pgn": row["pgn"].strip(),
            }

    # Merge stats by ECO code
    with open(stats_file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            eco = row[4]
            if eco in openings:
                openings[eco]["winrate"] = float(row[8])
                openings[eco]["drawrate"] = float(row[9])
                openings[eco]["avg_rating"] = (int(row[6]) + int(row[7])) / 2

    return openings

#Getting openings info
openings_dict = load_openings_with_stats(r"C:\Users\joelj\Desktop\Chess Coach\Chess_openings\openings.csv",r"C:\Users\joelj\Desktop\Chess Coach\Chess_openings(info)\openings.csv")

def detect_opening(board, openings_dict):
    # Get moves played so far in UCI list
    played_moves = [m.uci() for m in board.move_stack]

    for eco, data in openings_dict.items():
        opening_moves = data["uci"].split()

        # Match only if opening moves are a prefix of the played moves
        if played_moves[:len(opening_moves)] == opening_moves:
            return data

    return {"name": "Unknown", "eco": "?", "winrate": None, "drawrate": None, "avg_rating": None}

def _eval_to_pawns(eval_dict):
    """Convert stockfish get_evaluation() dict to a float (pawns, White-positive)."""
    if eval_dict is None:
        return 0.0
    t = eval_dict.get("type")
    v = eval_dict.get("value", 0)
    if t == "cp":
        return float(v) / 100.0
    if t == "mate":
        # represent mate as a very large advantage in pawns (signed)
        return 1000.0 if v > 0 else -1000.0
    return 0.0


def _material_balance(board):
    """
    Returns material balance (white_value - black_value) in pawns and
    a Counter of piece counts per color for diagnostics.
    """
    white_total = 0.0
    black_total = 0.0
    white_counts = Counter()
    black_counts = Counter()
    for sq, piece in board.piece_map().items():
        sym = piece.symbol()  # uppercase = White, lowercase = Black
        pv = _PIECE_VALUE.get(sym.upper(), 0.0)
        if piece.color == chess.WHITE:
            white_total += pv
            white_counts[sym.upper()] += 1
        else:
            black_total += pv
            black_counts[sym.upper()] += 1
    return (white_total - black_total), white_counts, black_counts


def _is_passed_pawn(board, square):
    """Return True if pawn at `square` is a passed pawn (no enemy pawns on same/adjacent files ahead)."""
    piece = board.piece_at(square)
    if not piece or piece.piece_type != chess.PAWN:
        return False
    file = chess.square_file(square)
    rank = chess.square_rank(square)
    enemy = not piece.color
    if piece.color == chess.WHITE:
        for f in (file - 1, file, file + 1):
            if 0 <= f < 8:
                for r in range(rank + 1, 8):
                    sq = chess.square(f, r)
                    p = board.piece_at(sq)
                    if p and p.piece_type == chess.PAWN and p.color == enemy:
                        return False
        return True
    else:  # black pawn
        for f in (file - 1, file, file + 1):
            if 0 <= f < 8:
                for r in range(0, rank):
                    sq = chess.square(f, r)
                    p = board.piece_at(sq)
                    if p and p.piece_type == chess.PAWN and p.color == enemy:
                        return False
        return True


def _count_pawns_on_file(board, file_index, color):
    """Count pawns of given color on a file (0..7)."""
    cnt = 0
    for r in range(8):
        sq = chess.square(file_index, r)
        p = board.piece_at(sq)
        if p and p.piece_type == chess.PAWN and p.color == color:
            cnt += 1
    return cnt

def get_cp_value(eval_dict):
    """Normalize stockfish eval to centipawns (int)."""
    if eval_dict is None:
        return 0
    t = eval_dict.get("type")
    v = eval_dict.get("value", 0)
    if t == "cp":
        return int(v)
    if t == "mate":
        return 100000 if v > 0 else -100000
    return 0

def detect_discovered_check_attack(board, move, moving_piece, eval_diff):
    reasons = []
    if board.is_check():
        checkers = list(board.checkers())
        if not checkers:
            return reasons

        # The piece that delivered check
        checker_sq = checkers[0]
        checker_piece = board.piece_at(checker_sq)

        # Look for additional attackers (apart from checker) that gained new threats
        for sq, piece in board.piece_map().items():
            if piece.color == moving_piece.color and sq != checker_sq:
                for target in board.attacks(sq):
                    target_piece = board.piece_at(target)
                    if target_piece and target_piece.color != piece.color:
                        # Prefer high-value or undefended pieces
                        defenders = board.attackers(target_piece.color, target)
                        if target_piece.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP) or len(defenders) == 0:
                            if eval_diff > 50:  # evaluation support (~0.5 pawns)
                                reasons.append(
                                    f"Discovered check AND {chess.piece_name(piece.piece_type)} now attacks "
                                    f"opponent’s {chess.piece_name(target_piece.piece_type)}."
                                )
    return reasons

def detect_discovered_double_attack(board, move, moving_piece, eval_diff):
    reasons = []
    if not moving_piece:
        return reasons

    # Primary piece’s new threats
    to_attacks = board.attacks(move.to_square)
    for target in to_attacks:
        target_piece = board.piece_at(target)
        if target_piece and target_piece.color != moving_piece.color:
            defenders = board.attackers(target_piece.color, target)

            if target_piece.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP) or len(defenders) == 0:
                # Look for a second piece (ally) that also gained new threats
                for sq, piece in board.piece_map().items():
                    if piece.color == moving_piece.color and sq != move.to_square:
                        for sec_target in board.attacks(sq):
                            sec_piece = board.piece_at(sec_target)
                            if sec_piece and sec_piece.color != piece.color:
                                sec_defenders = board.attackers(sec_piece.color, sec_target)
                                if sec_piece.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP) or len(sec_defenders) == 0:
                                    if eval_diff > 50:
                                        reasons.append(
                                            f"Discovered attack: {chess.piece_name(moving_piece.piece_type)} attacks "
                                            f"{chess.piece_name(target_piece.piece_type)} while "
                                            f"{chess.piece_name(piece.piece_type)} also threatens "
                                            f"{chess.piece_name(sec_piece.piece_type)}."
                                        )
    return reasons

def detect_deflection(board, move, moving_piece, eval_diff):
    reasons = []
    if not moving_piece:
        return reasons

    to_sq = move.to_square

    # -------------------------------
    # 1. Player performs a deflection
    # -------------------------------
    defenders = board.attackers(moving_piece.color, to_sq)
    attackers = board.attackers(not moving_piece.color, to_sq)

    if len(defenders) == 0 and len(attackers) > 0:
        for attacker_sq in attackers:
            attacker = board.piece_at(attacker_sq)
            if not attacker:
                continue

            for defended_sq in board.attacks(attacker_sq):
                defended_piece = board.piece_at(defended_sq)
                if defended_piece and defended_piece.color == moving_piece.color:
                    if defended_piece.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
                        if eval_diff > 50:
                            reasons.append(
                                f"Deflection tactic: tempted {chess.piece_name(attacker.piece_type)} "
                                f"away from defending your {chess.piece_name(defended_piece.piece_type)}."
                            )

    # ------------------------------------
    # 2. Player falls victim to deflection
    # ------------------------------------
    # Did moving_piece stop defending something important?
    for defended_sq in board.attacks(move.from_square):
        defended_piece = board.piece_at(defended_sq)
        if defended_piece and defended_piece.color == moving_piece.color:
            # Now check if it's still defended after the move
            still_defended = any(
                p.color == moving_piece.color for p in [board.piece_at(sq) for sq in board.attackers(moving_piece.color, defended_sq)]
            )
            if not still_defended and defended_piece.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
                if eval_diff < -50:  # Lost value
                    reasons.append(
                        f"Deflection blunder: your move abandoned the defense of your "
                        f"{chess.piece_name(defended_piece.piece_type)}, making it vulnerable."
                    )

    return reasons

def classify_move_with_reasons(board, move, stockfish, player_color, deep_brilliance_check=False):
    """
    Analyze a single move and return structured info (dict).
    Cleaned and corrected: snapshots taken in correct order, single board.pop(),
    dedupe reasons, robust labeling, skewer check confirmed by eval swing, piece activity inline.
    """

    # safety
    if move is None:
        return {"label": "Error", "reasons": ["No move provided"], "move_uci": None}
    board_copy = board.copy()

    # ---------- BEFORE MOVE SNAPSHOTS ----------
    # engine eval before (both cp and pawns)
    stockfish.set_fen_position(board.fen())
    eval_before = stockfish.get_evaluation()
    eval_before_pawns = _eval_to_pawns(eval_before)
    eval_before_cp = get_cp_value(eval_before)

    # best/top moves (before)
    try:
        best_move = stockfish.get_best_move()
    except Exception:
        best_move = None
    try:
        top_moves = stockfish.get_top_moves(3) or []
    except Exception:
        top_moves = []

    # material & counts before
    mat_before_balance, white_counts_before, black_counts_before = _material_balance(board)

    # piece activity: compute attacks-from BEFORE push (needed because after push 'from_square' may be empty)
    moving_piece = board.piece_at(move.from_square)
    if moving_piece and moving_piece.piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        from_attacks = list(board.attacks(move.from_square))
    else:
        from_attacks = []

    # captured piece detection (handle en passant)
    captured_piece_symbol = None
    try:
        if board.is_en_passant(move):
            cap_sq = move.to_square - 8 if board.turn == chess.WHITE else move.to_square + 8
            cap_piece = board.piece_at(cap_sq)
            if cap_piece:
                captured_piece_symbol = cap_piece.symbol().upper()
        elif board.is_capture(move):
            cap_piece = board.piece_at(move.to_square)
            if cap_piece:
                captured_piece_symbol = cap_piece.symbol().upper()
    except Exception:
        captured_piece_symbol = None

    # ---------- APPLY MOVE ----------
    board_copy.push(move)

    # ---------- AFTER MOVE SNAPSHOTS ----------
    stockfish.set_fen_position(board.fen())
    eval_after = stockfish.get_evaluation()
    eval_after_pawns = _eval_to_pawns(eval_after)
    eval_after_cp = get_cp_value(eval_after)

    try:
        top_moves_after = stockfish.get_top_moves(3) or []
    except Exception:
        top_moves_after = []

    mat_after_balance, white_counts_after, black_counts_after = _material_balance(board)

    # compute material change from player's POV (white_balance is white-black)
    mat_delta = mat_after_balance - mat_before_balance
    sign = 1.0 if player_color == chess.WHITE else -1.0
    material_change_for_player = mat_delta * sign

    # player-oriented evals (positive is good for player)
    player_eval_before = eval_before_pawns * sign
    player_eval_after = eval_after_pawns * sign
    player_eval_diff = player_eval_after - player_eval_before  # in pawns (float)

    # centipawn diff in engine sense (white-positive)
    cp_diff = eval_after_cp - eval_before_cp
    player_cp_diff = cp_diff * sign  # centipawns from player's POV

    reasons = []

    # ---------- 1. REASONS: capture / material ----------
    if captured_piece_symbol:
        reasons.append(f"Captured opponent's {captured_piece_symbol}.")
    if material_change_for_player > 0.0:
        reasons.append(f"Gained material: +{material_change_for_player:.2f} pawns.")
    elif material_change_for_player < 0.0:
        reasons.append(f"Lost material: {material_change_for_player:.2f} pawns.")

    # ---------- 2. REASONS: hanging / en prise ----------
    to_sq = move.to_square
    opponent_color = board.turn   # after push it's the opponent's turn
    our_color = not opponent_color
    moved_piece_now = board.piece_at(to_sq)
    if moved_piece_now:
        attackers = len(board.attackers(opponent_color, to_sq))
        defenders = len(board.attackers(our_color, to_sq))
        if attackers > 0 and attackers > defenders:
            reasons.append("The moved piece is now attacked and not sufficiently defended (left hanging).")

    # ---------- 3. REASONS: check / discovered checks ----------
    if board.is_check():
        reasons.append("Move gives check to the opponent (tactical/forcing).")

    # ---------- 4. REASONS: promotion ----------
    if move.promotion is not None:
        reasons.append(f"Pawn promoted to {chess.PIECE_NAMES[move.promotion]} (strong tactical/strategic effect).")

    # ---------- 5. REASONS: pawn structure (passed/doubled/isolated) ----------
    if moving_piece and moving_piece.piece_type == chess.PAWN:
        if _is_passed_pawn(board, to_sq):
            reasons.append("This pawn is now a passed pawn — strong endgame potential.")
        f = chess.square_file(to_sq)
        num_on_file = _count_pawns_on_file(board, f, moving_piece.color)
        if num_on_file >= 2:
            reasons.append("You now have doubled pawns on that file (structural weakness).")
        adj_files = [f - 1, f + 1]
        isolated = True
        for af in adj_files:
            if 0 <= af < 8 and _count_pawns_on_file(board, af, moving_piece.color) > 0:
                isolated = False
                break
        if isolated:
            reasons.append("This pawn is isolated (no friendly pawns on adjacent files).")

    # ---------- 6. REASONS: open file detection ----------
    file_idx = chess.square_file(to_sq)
    pawns_on_file_after = sum(
        1 for r in range(8)
        if (p := board.piece_at(chess.square(file_idx, r))) and p.piece_type == chess.PAWN
    )
    if pawns_on_file_after == 0:
        opponent_major_present = any(
            p for _, p in board.piece_map().items() if p.color == opponent_color and p.piece_type in (chess.ROOK, chess.QUEEN)
        )
        if opponent_major_present:
            reasons.append("This move opened a file that opponent's heavy pieces may exploit (open file).")

    # ---------- 7. REASONS: king safety heuristic ----------
    try:
        our_king_sq = board.king(our_color)
        if our_king_sq is not None and moving_piece and moving_piece.piece_type == chess.PAWN:
            king_file = chess.square_file(our_king_sq)
            moved_file = chess.square_file(move.from_square)
            if abs(king_file - moved_file) <= 1:
                reasons.append("Pawn moved from a file near your king — could weaken king safety.")
    except Exception:
        pass

    # ---------- 8. REASONS: tactical fork heuristic ----------
    attacked_opponent_pieces = 0
    attacked_high_value = 0
    # heuristic: consider squares attacked by our_color from to_sq (we want to count what the moved piece attacks)
    if moved_piece_now:
        attacked_sqs = list(board.attacks(to_sq))
        for sq in attacked_sqs:
            p = board.piece_at(sq)
            if p and p.color == opponent_color:
                attacked_opponent_pieces += 1
                if p.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
                    attacked_high_value += 1
    if attacked_high_value >= 2:
        reasons.append("Tactical fork/threat: this move attacks multiple high-value enemy pieces.")

    # ---------- 9. REASONS: eval improvement / collapse ----------
    if player_eval_diff >= 1.0:
        reasons.append("This move strongly improved your position (tactical or strategic breakthrough).")
    elif player_eval_diff >= 0.5:
        reasons.append("This move increased your advantage noticeably.")

    if player_eval_diff <= -3.0:
        reasons.append("Serious tactical loss / decisive material loss likely occurred.")
    elif player_eval_diff <= -1.5:
        reasons.append("This move substantially worsened the position (likely a mistake).")
    elif player_eval_diff <= -0.5:
        reasons.append("This move weakened your position (inaccuracy).")

    # --- 15. Deflection detection ---
    reasons.extend(detect_deflection(board, move, moving_piece, player_eval_diff * 100))

    # ---------- 11. Piece activity (inline, pre/post attack counts & quality) ----------
    if moving_piece and moving_piece.piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        # from_attacks computed before; compute to_attacks now (after move)
        to_attacks = list(board.attacks(move.to_square))
        diff_attacks = len(to_attacks) - len(from_attacks)

        if diff_attacks >= 2:
            reasons.append(
                f"{chess.piece_name(moving_piece.piece_type).capitalize()} became more active "
                f"(controls {len(from_attacks)} → {len(to_attacks)} squares)."
            )

        # central control
        central_squares = {
            chess.D4, chess.E4, chess.D5, chess.E5,
            chess.C3, chess.C4, chess.C5, chess.C6,
            chess.F3, chess.F4, chess.F5, chess.F6,
            chess.D3, chess.E3, chess.D6, chess.E6
        }
        if any(sq in to_attacks for sq in central_squares) and not any(sq in from_attacks for sq in central_squares):
            reasons.append(f"{chess.piece_name(moving_piece.piece_type).capitalize()} increased central influence.")

        # open file for rooks
        if moving_piece.piece_type == chess.ROOK:
            file_index = chess.square_file(move.to_square)
            if all(board.piece_at(chess.square(file_index, rank)) is None for rank in range(8)):
                reasons.append("Rook moved to an open file, maximizing its activity.")

        # bishop diagonal scope
        if moving_piece.piece_type == chess.BISHOP and len(to_attacks) >= len(from_attacks) + 2:
            reasons.append("Bishop gained more scope along its diagonal.")

        # directly attacking high-value pieces
        attacked_pieces = [board.piece_at(sq) for sq in to_attacks if board.piece_at(sq)]
        high_value = [p for p in attacked_pieces if p.piece_type in (chess.QUEEN, chess.ROOK)]
        if high_value:
            reasons.append(f"{chess.piece_name(moving_piece.piece_type).capitalize()} now attacks a valuable piece.")

    # ---------- 12. Skewer detection (inline, eval-confirmed) ----------
    if board.is_check():
        checking_squares = board.checkers()
        for checker_sq in checking_squares:
            checker_piece = board.piece_at(checker_sq)
            if checker_piece and checker_piece.piece_type in (chess.BISHOP, chess.ROOK, chess.QUEEN):
                king_sq = board.king(not checker_piece.color)

                if king_sq is None:
                    continue

                df = chess.square_file(king_sq) - chess.square_file(checker_sq)
                dr = chess.square_rank(king_sq) - chess.square_rank(checker_sq)

                # Normalize direction (e.g. bishop = diagonal, rook = straight)
                step_file = (df > 0) - (df < 0)
                step_rank = (dr > 0) - (dr < 0)

                behind_file = chess.square_file(king_sq) + step_file
                behind_rank = chess.square_rank(king_sq) + step_rank

                while 0 <= behind_file < 8 and 0 <= behind_rank < 8:
                    behind_sq = chess.square(behind_file, behind_rank)
                    victim = board.piece_at(behind_sq)
                    if victim and victim.color != checker_piece.color:
                        # Confirm eval swing
                        if player_cp_diff > 50:
                            reasons.append(
                                f"Skewer: {chess.piece_name(checker_piece.piece_type)} checks the king, "
                                f"and the {chess.piece_name(victim.piece_type)} behind it is vulnerable."
                            )
                        break
                    if victim:  # blocked
                        break
                    behind_file += step_file
                    behind_rank += step_rank

        
    # --- 13. Discovered Check + Attack ---
    reasons.extend(detect_discovered_check_attack(board, move, moving_piece, player_eval_diff * 100))

    # --- 14. Discovered Double Attack ---
    reasons.extend(detect_discovered_double_attack(board, move, moving_piece, player_eval_diff * 100))


    # ---------- DEDUPE REASONS (keep order) ----------
    seen = set()
    final_reasons = []
    for r in reasons:
        if r not in seen:
            final_reasons.append(r)
            seen.add(r)

    # ---------- LABELING: praise & blame combined ----------
    label = "Good Move"

    # engine-best exact match
    if best_move is not None and best_move == move.uci():
        label = "Best Move"
    else:
        # use player_eval_diff in pawns for thresholds (float)
        if player_eval_diff >= 1.0:
            label = "Brilliant"
        elif player_eval_diff >= 0.5:
            label = "Excellent"
        elif player_eval_diff >= 0.15:
            label = "Good"
        else:
            if player_eval_diff <= -3.0:
                label = "Blunder"
            elif player_eval_diff <= -1.5:
                label = "Mistake"
            elif player_eval_diff <= -0.5:
                label = "Inaccuracy"
            else:
                label = "Good Move"

    # optional deep brilliance check
    if deep_brilliance_check and label != "Best Move":
        try:
            stockfish.set_fen_position(board.fen())
            # some stockfish wrappers allow set_depth; wrap in try/except
            try:
                stockfish.set_depth(20)
            except Exception:
                pass
            deeper_best = stockfish.get_best_move()
            if deeper_best == move.uci():
                label = "Brilliant"
        except Exception:
            pass

    # ---------- PACKAGE RESULT ----------
    result = {
        "label": label,
        "eval_before": round(eval_before_pawns, 3),
        "eval_after": round(eval_after_pawns, 3),
        "player_eval_before": round(player_eval_before, 3),
        "player_eval_after": round(player_eval_after, 3),
        "player_eval_diff": round(player_eval_diff, 3),
        "material_change_for_player": round(material_change_for_player, 3),
        "captured_piece": captured_piece_symbol,
        "reasons": final_reasons,
        "best_move": best_move,
        "top_moves": top_moves,
        "top_moves_after": top_moves_after,
        "move_uci": move.uci()
    }

    return result

def coach_advice(board, player_move, stockfish, openings_dict, player_color, engine:str="groq"):
    # If player_move is a chess.Move, use it directly
    if isinstance(player_move, chess.Move):
        move = player_move
    elif isinstance(player_move, str):
        move = chess.Move.from_uci(player_move)
    else:
        raise ValueError("player_move must be a chess.Move or UCI string")

    #Classify the best move with reasons 
    move_explain = classify_move_with_reasons(board, move,stockfish=stockfish, player_color=player_color)

    #Getting the reason 
    reason = move_explain["reasons"]

    # --- Get Stockfish best move ---
    stockfish.set_fen_position(board.fen())
    best_move = move_explain["best_move"]
    top_moves = move_explain["top_moves"]
    evaluation = stockfish.get_evaluation()

    # --- Evaluation text ---
    state = evaluation.get("type")
    value = evaluation.get("value")

    if state == "cp":
        eval_cp = value / 100.0
        sign = 1 if player_color == chess.WHITE else -1
        eval_cp *= sign
        eval_text = f"Position eval: {eval_cp:+.1f}"
    elif state == "mate":
        eval_text = f"Mate in {abs(value)}"
    else:
        eval_text = "Equal position"
    

    best_move_text = f"Best move: {best_move}" if best_move else "No move found"

    # --- Detect opening ---
    opening_info = detect_opening(board, openings_dict)
    opening_text = f"Opening: {opening_info['name']} ({opening_info['eco']})"

    # Add stats if available
    stats_text = ""
    if opening_info.get("winrate") is not None:
        stats_text = (f"📊 Winrate: {opening_info['winrate']}%  "
                      f"Draw: {opening_info['drawrate']}%  "
                      f"Avg Rating: {opening_info['avg_rating']}")

    # --- Combine advice ---
    advice = [eval_text, best_move_text, opening_text, stats_text]

    # --- Draw panel ---
    panel_height = 100
    pygame.draw.rect(WIN, (30, 30, 30), (0, 0, WIDTH, panel_height))

    font = pygame.font.SysFont("Arial", 18, bold=True)
    y = 10
    for line in advice:
        if line:
            text_surface = font.render(line, True, (255, 255, 255))
            WIN.blit(text_surface, (10, y))
            y += 25
    
    # -- Return human readable explanation ---
    if engine == "gpt4all":
        # Flatten lists into strings
        reasons_text = "\n".join(reason) if isinstance(reason, list) else str(reason)
        top_moves_text = str(top_moves)

        query_text = "\n".join([
            reasons_text,
            eval_text,
            opening_text,
            stats_text,
            best_move_text,
            f"Top moves: {top_moves_text}"
        ])
        explain = query_local_gpt4all(query_text)

    elif engine == "groq":
        # Flatten lists into strings
        reasons_text = "\n".join(reason) if isinstance(reason, list) else str(reason)
        top_moves_text = str(top_moves)

        query_text = "\n".join([
            reasons_text,
            eval_text,
            opening_text,
            stats_text,
            best_move_text,
            f"Top moves: {top_moves_text}"
        ])
        explain = query_groq_llm(query_text)
    else:
        explain = None

    return explain

def draw_coach_panel(message):
    # Full-width strip at top
    pygame.draw.rect(WIN, (30, 30, 30), (0, 0, WIDTH + EVAL_WIDTH + 200, COACH_PANEL_HEIGHT))
    pygame.draw.line(WIN, (200, 200, 200), (0, COACH_PANEL_HEIGHT), (WIDTH + EVAL_WIDTH + 200, COACH_PANEL_HEIGHT), 2)

    # Message
    msg_label = font.render(str(message), True, (255, 255, 255))
    WIN.blit(msg_label, (20, 20))

    # Top 3 moves
    '''top_text = " / ".join([m['Move'] for m in top_moves])
    top_label = font.render(f"Top: {top_text}", True, (150, 200, 255))
    WIN.blit(top_label, (250, 55))'''

# Main loop
while running:
    clock.tick(60)
    draw_board()
    draw_captured_pieces()

    #Stockfish to update the new position
    stockfish.set_fen_position(board.fen())
    evaluation = stockfish.get_evaluation()

    draw_eval_bar(evaluation, player_color)
    update_piece_animations()
    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            square = get_square_from_mouse(event.pos)

            if square is None:
                continue

            if selected_square is None:
                # Select first square
                piece = board.piece_at(square)
                if piece and (piece.color == player_color) and board.turn == player_color:
                    selected_square = square
            else:
                # Try move
                move = chess.Move(selected_square, square)
                if move in board.legal_moves:
                    target_square = move.to_square
                    # Capture only if the target square had an opponent's piece
                    captured_piece = board.piece_at(target_square)
                    
                    if captured_piece is not None and captured_piece.color != board.turn:
                        # Opponent piece, add to captures
                        if captured_piece.color == chess.WHITE:
                            captured_white.append(captured_piece.symbol())
                        else:
                            captured_black.append(captured_piece.symbol())
                    
                    moving_piece = board.piece_at(move.from_square)
                    explain = coach_advice(board,move,stockfish,openings_dict,player_color)
                    board.push(move)
                    start_piece_animation(moving_piece, move.from_square, move.to_square)
                    stockfish.set_fen_position(board.fen())
                    selected_square = None
                    
                    print(explain)
                    draw_coach_panel(explain)

                    #Ai plays
                    if board.turn != player_color and not board.is_game_over():
                        ai_move()
        
                else:
                    selected_square = None

    pygame.display.flip()

pygame.quit()
