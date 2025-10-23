# MTGA Arena AI Coach

A desktop assistant that reads MTGA log files and provides heuristic-based recommendations for optimal lines of play.

## Features

- Real-time MTGA log parsing
- Game state reconstruction
- Heuristic-based play suggestions
- Electron overlay UI
- WebSocket event streaming

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Download Scryfall card data:
```bash
python data/scryfall_downloader.py
```

3. Run the log parser:
```bash
python parser/main.py
```

## Project Structure

- `/parser` - Log file tailer and event parser
- `/data` - Scryfall bulk data cache
- `/tests` - Sample log files for testing
- `/ui-overlay` - Electron-based overlay UI (Phase 5)

## Development

The parser runs continuously, tailing the MTGA log file and emitting structured events via WebSocket on `localhost:8765`.
