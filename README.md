README.md created for the repository — full contents below.

```markdown name=README.md
# AI Chess Coach

A local, interactive chess coach that combines a GUI chessboard, Stockfish engine analysis, a openings database, and optional LLM-powered human-friendly explanations. Intended for developers and hobbyists who want a playable chess UI with move classification and short coaching messages.

## Highlights
- Play against Stockfish (engine-driven AI moves).
- Move classification with human-readable "reasons" (captures, tactics, pawn structure, king safety, forks, skewers, etc.).
- Opening detection using included opening databases (CSV).
- Optional LLM explanations:
  - Local GPT4All model support (requires a GGUF model file).
  - Remote LLM via GROQ API (requires `GROQ_API_KEY`).
- Two UI options:
  - Pygame-based interactive board + coach (`main.py`).
  - DearPyGui front-end (`Frontend/frontend.py`) — alternate UI mockup.

---

## Repository structure (top-level)
```
.gitignore
Chess_openings/                 # Primary openings CSV used by the app
Chess_openings(info)/           # Additional openings/stats CSV files
Frontend/                       # DearPyGui frontend implementation
assets/                         # Piece PNGs used by both frontends
chess-pieces-png/               # (duplicate/unpacked assets)
chess-pieces-png.zip            # piece images zip
main.py                         # Pygame main application (engine + coach)
test.py                         # GROQ API test helper
test_1.py                       # stray snippet (not used)
stockfish-windows-x86-64-avx2/  # bundled Windows Stockfish binary (zipped copy present)
stockfish-windows-x86-64-avx2.zip
```

How it fits together:
- `main.py` is the primary playable application. It draws the board with pygame, communicates with Stockfish for evaluations/moves, loads opening data (CSV files), and prepares short coaching text. The coach can optionally call an LLM (local GPT4All or remote GROQ) to rephrase and expand reasons.
- `Frontend/frontend.py` is a separate UI implemented with DearPyGui (loads the same piece assets) that demonstrates a different GUI approach but not the engine/coach integration.

---

## Requirements
Recommended: Python 3.10+ (3.8+ may work but newer versions are preferred).

Python packages used by the code:
- pygame
- python-chess
- stockfish (Python wrapper)
- gpt4all (optional — for local LLM)
- requests
- dearpygui (only for `Frontend/frontend.py`)
- (standard libs: os, math, csv, collections, etc.)

Suggested install command:
```bash
python -m pip install pygame python-chess stockfish gpt4all requests dearpygui
```
(Install only the ones you need — e.g., skip `gpt4all` if you won't use the local LLM, and skip `dearpygui` if you won't run the Frontend.)

---

## Quick start — run the pygame coach (main experience)
1. Clone the repo and unzip stockfish if desired (the repo contains a Windows build zipped):
   - If you're on Windows you can use the included ZIP, otherwise download Stockfish for your OS from https://stockfishchess.org/download/.
2. Ensure the piece image files exist in `assets/` (they are included).
3. Adjust configuration in `main.py` (two changes you should make):
   - Stockfish path: by default the code hardcodes a Windows path:
     ```py
     stockfish = Stockfish(path=r"C:\Users\joelj\Desktop\Chess Coach\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe")
     ```
     Change that to point at your local stockfish binary, for example:
     ```py
     stockfish = Stockfish(path="/usr/local/bin/stockfish")  # macOS/Linux
     # or
     stockfish = Stockfish(path=r"C:\path\to\stockfish.exe")  # Windows
     ```
   - Openings CSV paths: `main.py` currently loads openings from an absolute path. Update this call to use the repo-relative files:
     ```py
     openings_dict = load_openings_with_stats("Chess_openings/openings.csv", "Chess_openings(info)/openings.csv")
     ```
4. (Optional) If you want LLM explanations using GROQ:
   - Export your API key:
     ```bash
     export GROQ_API_KEY="your_key_here"       # macOS / Linux
     setx GROQ_API_KEY "your_key_here"         # Windows (or use set in the session)
     ```
   - The default engine in `coach_advice` is `"groq"`. To use local GPT4All, call or change the engine parameter to `"gpt4all"` and make sure you have a GGUF model available (the code expects `"gpt4all-falcon-q4_0.gguf"` by default).
5. Run the app:
```bash
python main.py
```
- Choose White or Black in the menu.
- Click to select/move pieces. The app prints coach messages to console and draws a short panel.

---

## Run the DearPyGui frontend (alternate)
This script is a UI mock and is separate from the engine logic:
```bash
python Frontend/frontend.py
```
Ensure `dearpygui` is installed and `assets/` is present. This frontend does not run Stockfish or the coach logic by itself — it's a UI showcase that expects the same piece assets.

---

## Files of interest
- `main.py` — main game loop, engine integration, move classification, animation, and coach pipeline.
- `Frontend/frontend.py` — alternate UI built with DearPyGui.
- `Chess_openings/openings.csv` — detailed openings file used for detection.
- `Chess_openings(info)/openings.csv` — opening statistics merged into the app.
- `assets/` — PNG images for chess pieces.
- `stockfish-windows-x86-64-avx2.zip` — bundled Windows engine binary (you must extract and point `main.py` at the extracted `.exe`).

---

## Configuration notes & tips
- Paths in code: `main.py` currently contains absolute Windows paths. Edit these lines to use relative paths or environment variables so the project runs cross-platform.
- LLM choices:
  - Local GPT4All: requires the model file (`.gguf`), disk space, and the `gpt4all` package.
  - GROQ: requires `GROQ_API_KEY` environment variable and network access. The code posts to `https://api.groq.com/openai/v1/chat/completions`.
- Stockfish wrapper: the `stockfish` Python package expects the path to the engine binary; make sure the version you download is compatible.

---

## Known issues & TODOs
- Hardcoded absolute paths (Stockfish and openings) should be parameterized (env vars or config file).
- No requirements.txt provided — you may want to add one.
- Some files (e.g., `test_1.py`) appear to be leftover fragments and can be removed/cleaned.
- The openings CSVs are large; loading them can be slow and memory-heavy. Consider using a lighter index or a cached subset for faster startup.
- No license file is present — add a LICENSE if you plan to open-source this project.

---

## Contributing
- If you'd like to contribute:
  - Open issues for bugs or feature requests.
  - Send PRs that:
    - Replace absolute paths with configurable options.
    - Add a requirements.txt and a small install script.
    - Add cross-platform checks for the Stockfish binary.
    - Add tests / CI for parts of the classification logic.

---

## Example edits (recommended)
Replace the hardcoded stockfish path with an environment-driven helper:
```py
# at top of main.py
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "/usr/local/bin/stockfish")
stockfish = Stockfish(path=STOCKFISH_PATH)
```
And set:
```bash
export STOCKFISH_PATH="/path/to/stockfish"
```

Change openings load to repo-relative:
```py
openings_dict = load_openings_with_stats("Chess_openings/openings.csv", "Chess_openings(info)/openings.csv")
```

---

## Acknowledgements
- Stockfish (open-source engine) for evaluation and best-move suggestions.
- GPT4All / GROQ (optional) for natural-language explanations.
- python-chess, pygame, and DearPyGui for utilities and UIs.

---
