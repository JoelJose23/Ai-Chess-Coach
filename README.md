♟️ AI Chess Coach
An AI-powered chess coaching application that analyzes your moves in real time, explains why a move is good or bad, detects openings, evaluates positions using Stockfish, and generates human-like coaching advice using an LLM.
Built with Python, Stockfish, and a custom reasoning engine — designed to feel like a personal chess mentor, not just an evaluation bar.
✨ Features
🧠 Move Classification
Labels moves as Brilliant, Best, Excellent, Good, Inaccuracy, Mistake, or Blunder
Based on evaluation swings, material changes, and tactical patterns
📊 Stockfish Evaluation
Centipawn & mate evaluations
Best move and top engine continuations
📝 Human-Readable Explanations
Explains why a move is good or bad
Uses an LLM (Groq / compatible API) for natural coaching-style feedback
📚 Opening Detection
Matches played moves against an ECO opening database
Displays opening name, ECO code, win rate, draw rate, and average rating
🎯 Tactical & Strategic Insights
Detects:
Hanging pieces
Forks
Skewers
Discovered attacks/checks
Pawn structure issues
King safety weaknesses
Piece activity improvements
🖥️ Interactive Chess GUI
Built with Pygame
Visual board, captured pieces, evaluation bar, and coach panel
🛠️ Tech Stack
Python 3.10+
python-chess
Stockfish
Pygame
LLM API (Groq or compatible)
CSV-based ECO Opening Database
