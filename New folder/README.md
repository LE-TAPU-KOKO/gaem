# Enhanced Devilish Platformer

A challenging platformer game built with Pygame and adapted for web deployment using Pygbag.

## Game Features

- Challenging platformer gameplay with double jump mechanics
- Multiple obstacles including spikes, falling stones, and magic walls
- Particle effects and camera shake for enhanced feedback
- Atmospheric visual effects
- Responsive controls

## How to Play

- **Move**: A/D or Left/Right arrow keys
- **Jump**: W, Up arrow, or Space (Double jump available!)
- **Reset**: R
- **Quit**: ESC

## Web Deployment Instructions

### Prerequisites

- Python 3.8 or higher
- Pygame CE (Community Edition)
- Pygbag

### Installation

```bash
pip install pygame-ce
pip install pygbag
```

### Deploying to Web

1. Make sure your main game file is named `main.py` (already done)
2. Run the following command from the game directory:

```bash
pygbag --ume_block 0 .
```

3. Open a web browser and navigate to http://localhost:8000

### Building for Distribution

To build the game for web distribution:

```bash
pygbag --build .
```

This will create a `build` directory with the web-ready files.

## Important Notes for Web Compatibility

- The game has been modified to use `asyncio.sleep(0)` in the main loop for browser compatibility
- A favicon.png file is included for web display
- The game uses pixelated rendering style for better appearance on web
- If you need to add audio files, make sure they are in OGG format for web compatibility

## Troubleshooting

If you encounter issues with the web deployment:

1. Make sure you're using the latest version of pygbag
2. Check that all file paths use forward slashes (`/`) instead of backslashes
3. Ensure all filenames are case-sensitive consistent
4. For WebGL content, add `--template noctx.tmpl` to the pygbag command

## Credits

Created with Pygame and adapted for web using Pygbag.