#TerXTubE

# README for TerxTube - Terminal YouTube Player

## About This Tool

TerxTube is a powerful command-line YouTube player and downloader that brings YouTube functionality to your terminal. Designed for Linux (including Termux), macOS, and Windows, this tool allows you to:

- Search and play YouTube videos directly in your terminal
- Download videos or audio in various qualities
- Maintain a watch history
- Copy video URLs to clipboard
- Control playback with keyboard shortcuts

With its intuitive interface and minimal dependencies, TerxTube is perfect for users who prefer keyboard-driven applications or need lightweight YouTube access.

## Installation Process

### Prerequisites
- Python 3.6 or higher
- pip package manager

### Installation Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/terxtube.git
   cd terxtube
   ```

2. **Install dependencies** (the tool will check and install automatically, but you can manually install them):
   ```bash
   # For Linux/Termux:
   pkg install python ffmpeg mpv termux-api -y

   # For macOS (using Homebrew):
   brew install python ffmpeg mpv

   # For Windows (using Chocolatey):
   choco install python ffmpeg mpv

   # Then install Python dependencies:
   pip install requests beautifulsoup4 yt-dlp
   ```

3. **Make the script executable** (Linux/macOS):
   ```bash
   chmod +x terxtube.py
   ```

4. **Run the application**:
   ```bash
   python terxtube.py
   # or ./terxtube.py if executable
   ```

## User Manual

### Main Menu Options
1. **Search and Play**: Search YouTube videos and play/download them
2. **Play with URL**: Directly play a video using its YouTube URL
3. **View History**: See and replay your recently watched videos
4. **Exit**: Quit the application

### During Playback Controls
- Press `p` to pause/resume playback
- Press `q` to stop playback and return to the menu

### Search and Play Features
- Enter your search query to find YouTube videos
- Select a video by entering its number
- Download videos by entering `d` followed by the video number (e.g., `d2` for video 2)
- Choose between video or audio-only playback
- Select video quality when available

### Download Options
- Videos are saved to:
  - `Downloads/YouTube_Videos` for video files
  - `Downloads/YouTube_Audios` for audio files
- You can specify quality during download

### Clipboard Support
- The tool automatically copies video URLs to your clipboard when playing
- Supported on Linux (Termux), macOS, and Windows

### History Features
- Recently watched videos are automatically saved
- You can replay or download videos from your history
- History is limited to the last 50 watched videos

### Notes
- For best performance on mobile (Termux), use audio-only mode
- The application checks for required dependencies on startup
- All operations can be cancelled with Ctrl+C

Enjoy your terminal-based YouTube experience with TerxTube!
