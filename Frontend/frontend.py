# frontend.py
import os
import dearpygui.dearpygui as dpg

# --- Layout & styling ---
BOARD_SIZE = 650
SQ = BOARD_SIZE // 8
LEFT_STRIP = 40       # solid black strip on the left (screenshot look)
TOP_PADDING = 100     # room for dialog bar
RIGHT_MARGIN = 8     # subtle empty space
DRAW_INSET = 4        # inset pieces inside a square to avoid clipping
CAPTURE_WIDTH = 220  # width of capture display area

LIGHT = (240, 217, 181, 255)
DARK  = (181, 136,  99, 255)
BORDER = (60, 60, 60, 255)
WHITE_FILL = (240, 240, 240, 255)
BLACK_FILL = (20, 20, 20, 255)
DIALOG_BG  = (36, 36, 36, 255)
DIALOG_TXT = (240, 240, 240, 255)

# --- Global UI state ---
player_color = "white"  # "white" or "black"
piece_textures = {}     # code -> texture tag

# --- Assets to load ---
ASSET_FILES = {
    "wp": "assets/wp.png",
    "wn": "assets/wn.png",
    "wb": "assets/wb.png",
    "wr": "assets/wr.png",
    "wq": "assets/wq.png",
    "wk": "assets/wk.png",
    "bp": "assets/bp.png",
    "bn": "assets/bn.png",
    "bb": "assets/bb.png",
    "br": "assets/br.png",
    "bq": "assets/bq.png",
    "bk": "assets/bk.png",
}

# Standard initial setup (row 0 = rank 1, row 7 = rank 8)
INITIAL_MATRIX = [
    ["wr", "wn", "wb", "wq", "wk", "wb", "wn", "wr"],  # rank 1
    ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],  # rank 2
    ["",   "",   "",   "",   "",   "",   "",   "" ],  # rank 3
    ["",   "",   "",   "",   "",   "",   "",   "" ],  # rank 4
    ["",   "",   "",   "",   "",   "",   "",   "" ],  # rank 5
    ["",   "",   "",   "",   "",   "",   "",   "" ],  # rank 6
    ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],  # rank 7
    ["br", "bn", "bb", "bq", "bk", "bb", "bn", "br"],  # rank 8
]

def make_no_padding_theme():
    with dpg.theme(tag="no_pad_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,   4, 4, category=dpg.mvThemeCat_Core)

def load_piece_textures():
    """Load all piece textures into a texture_registry once."""
    with dpg.texture_registry(tag="tex_registry"):
        for code, path in ASSET_FILES.items():
            if not os.path.exists(path):
                raise FileNotFoundError(f"Missing asset: {path}")
            w, h, c, data = dpg.load_image(path)
            tex_tag = f"tex_{code}"
            dpg.add_static_texture(w, h, data, tag=tex_tag)
            piece_textures[code] = tex_tag

def draw_left_strip():
    dpg.delete_item("strip_draw", children_only=True)
    h = BOARD_SIZE
    # Solid black strip (no split bar) like in the screenshot
    dpg.draw_rectangle((0, 0), (LEFT_STRIP-1, h-1), color=(0,0,0,255), fill=(0,0,0,255), parent="strip_draw")

def draw_dialog(text="Hello player"):
    dpg.delete_item("dialog_draw", children_only=True)
    H = 64
    W = LEFT_STRIP + BOARD_SIZE + RIGHT_MARGIN
    dpg.draw_rectangle((0, 0), (W-1, H-1), color=DIALOG_BG, fill=DIALOG_BG, parent="dialog_draw")
    # Draw white text; if your DPG has no size arg, it will use default font size
    try:
        dpg.draw_text((10, 18), text, color=DIALOG_TXT, size=28, parent="dialog_draw")
    except TypeError:
        dpg.draw_text((10, 18), text, color=DIALOG_TXT, parent="dialog_draw")

def draw_board_with_pieces():
    """Draw board squares then piece sprites scaled to each square with an inset to avoid clipping."""
    dpg.delete_item("board_draw", children_only=True)

    # Outer border
    dpg.draw_rectangle((0, 0), (BOARD_SIZE-1, BOARD_SIZE-1), color=BORDER, fill=(0,0,0,0), parent="board_draw")

    # Orientation mapping
    if player_color == "white":
        row_indices = list(range(7, -1, -1))   # visual row 0 -> matrix row 7 (rank 8)
        col_indices = list(range(0, 8))        # A..H
    else:
        row_indices = list(range(0, 8))        # visual row 0 -> matrix row 0
        col_indices = list(range(7, -1, -1))   # H..A

    # Draw squares + pieces
    for vr, mr in enumerate(row_indices):
        for vc, mc in enumerate(col_indices):
            x0, y0 = vc * SQ, vr * SQ
            x1, y1 = x0 + SQ, y0 + SQ

            # Square
            color = LIGHT if (mr + mc) % 2 == 0 else DARK
            dpg.draw_rectangle((x0, y0), (x1, y1), color=(40,40,40,180), fill=color, parent="board_draw")

            # Piece inset to avoid edge clipping
            code = INITIAL_MATRIX[mr][mc]
            if code:
                tex = piece_textures.get(code)
                if tex:
                    inset = DRAW_INSET
                    dpg.draw_image(tex, (x0 + inset, y0 + inset), (x1 - inset, y1 - inset),
                                   uv_min=(0,0), uv_max=(1,1), parent="board_draw")

def start_game(selected_color: str):
    global player_color
    player_color = selected_color
    dpg.hide_item("menu_win")
    if not dpg.does_item_exist("game_win"):
        build_game_window()
    draw_dialog("Hello player")
    draw_left_strip()
    draw_board_with_pieces()
    dpg.show_item("game_win")

def on_white():
    start_game("white")

def on_black():
    start_game("black")

def on_exit():
    dpg.stop_dearpygui()

def build_menu_window():
    total_w = LEFT_STRIP + BOARD_SIZE + RIGHT_MARGIN + CAPTURE_WIDTH
    with dpg.window(tag="menu_win", label="Menu", width=total_w, height=160, no_resize=True, no_collapse=True, no_move=True):
        dpg.add_text("Choose your side")
        dpg.add_spacer(height=6)
        with dpg.group(horizontal=True):
            dpg.add_button(label="White", width=120, height=40, callback=on_white)
            dpg.add_button(label="Black", width=120, height=40, callback=on_black)
            dpg.add_button(label="Exit",  width=120, height=40, callback=on_exit)

def build_game_window():
    total_w = LEFT_STRIP + BOARD_SIZE + RIGHT_MARGIN + CAPTURE_WIDTH
    total_h = BOARD_SIZE + TOP_PADDING

    with dpg.window(tag="game_win", label="Chess Coach", width=total_w, height=total_h, show=False):

        # Dialog bar (banner)
        with dpg.child_window(tag="dialog_panel", width=total_w, height=64,
                            border=False, no_scrollbar=True, no_scroll_with_mouse=True):
            with dpg.drawlist(width=total_w, height=64, tag="dialog_draw"):
                pass

        # Row: left strip | board | captured
        with dpg.group(horizontal=True):
            # Left solid strip
            with dpg.child_window(tag="strip_panel", width=LEFT_STRIP, height=BOARD_SIZE,
                                border=False, no_scrollbar=True, no_scroll_with_mouse=True):
                with dpg.drawlist(width=LEFT_STRIP, height=BOARD_SIZE, tag="strip_draw"):
                    pass
            dpg.bind_item_theme("strip_panel", "no_pad_theme")

            # Board panel
            with dpg.child_window(tag="board_panel", width=BOARD_SIZE+2, height=BOARD_SIZE+2,
                                border=True, no_scrollbar=True, no_scroll_with_mouse=True):
                with dpg.drawlist(width=BOARD_SIZE, height=BOARD_SIZE, tag="board_draw"):
                    pass
            dpg.bind_item_theme("board_panel", "no_pad_theme")

            # Captured panel (right)
            with dpg.child_window(tag="captured_panel", width=CAPTURE_WIDTH, height=BOARD_SIZE,
                                border=True, no_scrollbar=True, no_scroll_with_mouse=True):
                dpg.add_text("Captured pieces")
                dpg.add_spacer(height=6)
                # White captures area (top half)
                with dpg.child_window(tag="cap_white", width=-1, height=BOARD_SIZE//2 - 20,
                                    border=True, no_scrollbar=True, no_scroll_with_mouse=True):
                    dpg.add_text("White captures")
                dpg.bind_item_theme("cap_white", "no_pad_theme")
                # Black captures area (bottom half)
                with dpg.child_window(tag="cap_black", width=-1, height=BOARD_SIZE//2 - 20,
                                    border=True, no_scrollbar=True, no_scroll_with_mouse=True):
                    dpg.add_text("Black captures")
                dpg.bind_item_theme("cap_black", "no_pad_theme")
        dpg.bind_item_theme("captured_panel", "no_pad_theme")


if __name__ == "__main__":
    dpg.create_context()
    make_no_padding_theme()
    load_piece_textures()
    build_menu_window()
    dpg.create_viewport(title="Chess Coach UI", width=LEFT_STRIP + BOARD_SIZE + RIGHT_MARGIN + CAPTURE_WIDTH +15,
                        height=BOARD_SIZE + TOP_PADDING + 35)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()