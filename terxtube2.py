# TerXTubE2.py - Enhanced YouTube Player & Downloader with Modern Features

import os
import re
import sys
import json
import time
import signal
import shutil
import select
import platform
import subprocess
import threading
import hashlib
from pathlib import Path
from urllib.parse import urlparse, quote, parse_qs
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Try importing optional modern features
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import (
        Progress, BarColumn, TextColumn, TimeRemainingColumn, 
        TransferSpeedColumn, DownloadColumn, ProgressColumn
    )
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

# Text Styling with Theme Support
class Colors:
    # Default colors (will be overridden by theme)
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    
    @classmethod
    def apply_theme(cls, theme_name: str):
        """Apply color theme"""
        themes = {
            'dark': {
                'RED': '\033[91m', 'GREEN': '\033[92m', 'YELLOW': '\033[93m',
                'BLUE': '\033[94m', 'MAGENTA': '\033[95m', 'CYAN': '\033[96m',
                'WHITE': '\033[97m', 'RESET': '\033[0m', 'BOLD': '\033[1m',
                'UNDERLINE': '\033[4m', 'DIM': '\033[2m', 'BLINK': '\033[5m',
                'REVERSE': '\033[7m'
            },
            'light': {
                'RED': '\033[31m', 'GREEN': '\033[32m', 'YELLOW': '\033[33m',
                'BLUE': '\033[34m', 'MAGENTA': '\033[35m', 'CYAN': '\033[36m',
                'WHITE': '\033[30m', 'RESET': '\033[0m', 'BOLD': '\033[1m',
                'UNDERLINE': '\033[4m', 'DIM': '\033[2m', 'BLINK': '\033[5m',
                'REVERSE': '\033[7m'
            },
            'hacker': {
                'RED': '\033[38;5;196m', 'GREEN': '\033[38;5;46m', 
                'YELLOW': '\033[38;5;226m', 'BLUE': '\033[38;5;39m',
                'MAGENTA': '\033[38;5;201m', 'CYAN': '\033[38;5;51m',
                'WHITE': '\033[38;5;15m', 'RESET': '\033[0m', 'BOLD': '\033[1m',
                'UNDERLINE': '\033[4m', 'DIM': '\033[2m', 'BLINK': '\033[5m',
                'REVERSE': '\033[7m'
            },
            'neon': {
                'RED': '\033[38;5;198m', 'GREEN': '\033[38;5;121m',
                'YELLOW': '\033[38;5;227m', 'BLUE': '\033[38;5;75m',
                'MAGENTA': '\033[38;5;207m', 'CYAN': '\033[38;5;123m',
                'WHITE': '\033[38;5;231m', 'RESET': '\033[0m', 'BOLD': '\033[1m',
                'UNDERLINE': '\033[4m', 'DIM': '\033[2m', 'BLINK': '\033[5m',
                'REVERSE': '\033[7m'
            }
        }
        theme = themes.get(theme_name, themes['dark'])
        for key, value in theme.items():
            setattr(cls, key, value)

colors = Colors()

@dataclass
class AudioMetadata:
    """Enhanced audio metadata structure"""
    title: str = ''
    artist: str = ''
    album: str = 'YouTube Audio'
    album_artist: str = ''
    genre: str = ''
    year: str = ''
    track_number: int = 0
    track_total: int = 0
    disc_number: int = 0
    disc_total: int = 0
    composer: str = ''
    conductor: str = ''
    copyright: str = ''
    description: str = ''
    lyrics: str = ''
    comment: str = ''
    rating: float = 0.0
    bpm: int = 0
    mood: str = ''
    cover_art: bytes = None
    publisher: str = ''
    isrc: str = ''
    language: str = 'en'
    date: str = ''
    original_date: str = ''
    encoded_by: str = 'TerXTubE2'
    encoder: str = 'yt-dlp'
    media_type: str = 'Audio'
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

class Config:
    """Configuration management with settings persistence"""
    def __init__(self):
        self.config_dir = Path("config")
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "settings.json"
        self.defaults = {
            'theme': 'dark',
            'video_quality': 'best',
            'audio_quality': '192',
            'audio_format': 'mp3',
            'video_format': 'mp4',
            'download_path': str(Path.home() / "Downloads" / "YouTube"),
            'auto_organize': True,
            'subtitles': False,
            'subtitle_lang': 'en',
            'check_updates': True,
            'show_progress': True,
            'max_history': 50,
            'concurrent_downloads': 1
        }
        self.settings = self.load()
    
    def load(self) -> Dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved = json.load(f)
                    for key, value in self.defaults.items():
                        if key not in saved:
                            saved[key] = value
                    return saved
            except:
                return self.defaults.copy()
        return self.defaults.copy()
    
    def save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f, indent=4)
    
    def get(self, key: str, default=None):
        return self.settings.get(key, default)
    
    def set(self, key: str, value):
        self.settings[key] = value
        self.save()

class DependencyManager:
    @staticmethod
    def check_and_install():
        required = {
            'system': ['mpv', 'python', 'ffmpeg', 'termux-api'],
            'python': ['requests', 'beautifulsoup4', 'yt-dlp', 'mutagen']
        }

        print(f"{colors.BLUE}[*] Checking dependencies...{colors.RESET}")
        
        missing_system = []
        for pkg in required['system']:
            if not DependencyManager._check_system_package(pkg):
                missing_system.append(pkg)
        
        missing_python = []
        for pkg in required['python']:
            try:
                __import__(pkg.split('-')[0])
            except ImportError:
                missing_python.append(pkg)
        
        if missing_system or missing_python:
            print(f"{colors.YELLOW}[!] Installing missing packages...{colors.RESET}")
            DependencyManager._install_packages(missing_system, missing_python)
        
        print(f"{colors.GREEN}[+] All dependencies are satisfied!{colors.RESET}")
        time.sleep(1)

    @staticmethod
    def _check_system_package(pkg):
        return shutil.which(pkg) is not None

    @staticmethod
    def _install_packages(system_pkgs, python_pkgs):
        if system_pkgs:
            try:
                subprocess.run(['pkg', 'install', '-y'] + system_pkgs,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            except:
                pass
        
        if python_pkgs:
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install'] + python_pkgs,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            except:
                pass

def show_banner():
    banner = f"""
{colors.YELLOW}{colors.BOLD}
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║  ████████╗███████╗██████╗ ██╗  ██╗████████╗██╗   ██╗██████╗ ███████╗       ║
║  ╚══██╔══╝██╔════╝██╔══██╗╚██╗██╔╝╚══██╔══╝██║   ██║██╔══██╗██╔════╝       ║
║     ██║   █████╗  ██████╔╝ ╚███╔╝    ██║   ██║   ██║██████╔╝█████╗         ║
║     ██║   ██╔══╝  ██╔══██╗ ██╔██╗    ██║   ██║   ██║██╔══██╗██╔══╝         ║
║     ██║   ███████╗██║  ██║██╔╝ ██╗   ██║   ╚██████╔╝██║  ██║███████╗       ║
║     ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝       ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
{colors.RESET}
"""
    print(banner)

def show_enhanced_banner():
    """Enhanced banner with more style"""
    if RICH_AVAILABLE:
        console = Console()
        banner = f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║  ████████╗███████╗██████╗ ██╗  ██╗████████╗██╗   ██╗██████╗ ███████╗       ║
║  ╚══██╔══╝██╔════╝██╔══██╗╚██╗██╔╝╚══██╔══╝██║   ██║██╔══██╗██╔════╝       ║
║     ██║   █████╗  ██████╔╝ ╚███╔╝    ██║   ██║   ██║██████╔╝█████╗         ║
║     ██║   ██╔══╝  ██╔══██╗ ██╔██╗    ██║   ██║   ██║██╔══██╗██╔══╝         ║
║     ██║   ███████╗██║  ██║██╔╝ ██╗   ██║   ╚██████╔╝██║  ██║███████╗       ║
║     ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝       ║
║                                                                            ║
║              ╔══════════════════════════════════════════════╗              ║
║              ║  [bold cyan]Advanced YouTube Player & Downloader[/bold cyan]  ║
║              ║       [yellow]Version 2.0 - Modern Features[/yellow]         ║
║              ╚══════════════════════════════════════════════╝              ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"""
        console.print(banner)
    else:
        show_banner()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

class MetadataExtractor:
    """Advanced metadata extraction from YouTube videos"""
    
    @staticmethod
    def extract_artist_info(video_info: Dict) -> Tuple[str, str, str]:
        """
        Extract artist information from video metadata
        Returns: (artist, album_artist, composer)
        """
        artist = 'Unknown Artist'
        album_artist = ''
        composer = ''
        
        # 1. Uploader/channel name (most common)
        if video_info.get('uploader'):
            artist = video_info['uploader']
            album_artist = video_info['uploader']
        
        # 2. Check if it's a music video
        if video_info.get('categories'):
            categories = video_info['categories']
            if any(cat in str(categories).lower() for cat in ['music', 'song', 'artist']):
                title = video_info.get('title', '')
                # Try "Artist - Title" format
                artist_match = re.match(r'^(.+?)\s*[-–:]\s*(.+?)(?:\s*\(.*\))?$', title)
                if artist_match:
                    potential_artist = artist_match.group(1).strip()
                    if len(potential_artist) < 50:
                        artist = potential_artist
                        album_artist = potential_artist
                
                # Try "Title by Artist" format
                by_match = re.search(r'(.+?)\s+by\s+(.+?)(?:\s*\(.*\))?$', title, re.I)
                if by_match:
                    artist = by_match.group(2).strip()
                    album_artist = artist
        
        # 3. Check tags for artist information
        if video_info.get('tags'):
            tags = video_info['tags']
            for tag in tags:
                tag_lower = tag.lower()
                if 'artist' in tag_lower or 'singer' in tag_lower or 'vocal' in tag_lower:
                    artist_match = re.search(r'(?:artist|singer)[\s:]+(.+)', tag, re.I)
                    if artist_match:
                        artist = artist_match.group(1).strip()
                        break
        
        # 4. Check description for artist info
        if video_info.get('description'):
            description = video_info['description']
            patterns = [
                r'(?:Artist|Singer|Vocal|Music by)[\s:]+(.+?)(?:\n|$)',
                r'(?:Song by|Performed by)[\s:]+(.+?)(?:\n|$)',
                r'(?:©|℗)\s*(.+?)(?:\n|$)',
                r'(?:feat\.?|ft\.?)\s*(.+?)(?:\n|$)'
            ]
            for pattern in patterns:
                match = re.search(pattern, description, re.I)
                if match:
                    potential_artist = match.group(1).strip()
                    if potential_artist and not potential_artist.startswith('http'):
                        artist = potential_artist
                        break
        
        # 5. Check channel_url for channel name
        if video_info.get('channel_url'):
            channel_name = video_info['channel_url'].split('/')[-1]
            if channel_name and len(channel_name) < 30:
                artist = channel_name.replace('@', '')
        
        return artist, album_artist, composer
    
    @staticmethod
    def extract_full_metadata(video_info: Dict) -> AudioMetadata:
        """Extract complete metadata for audio tagging"""
        metadata = AudioMetadata()
        
        # Basic info
        metadata.title = video_info.get('title', 'Unknown Title')
        metadata.description = video_info.get('description', '')
        metadata.date = video_info.get('upload_date', '')
        
        if metadata.date and len(metadata.date) >= 4:
            metadata.year = metadata.date[:4]
        
        # Artist info
        artist, album_artist, composer = MetadataExtractor.extract_artist_info(video_info)
        metadata.artist = artist
        metadata.album_artist = album_artist or artist
        metadata.composer = composer
        
        # Album info
        if video_info.get('album'):
            metadata.album = video_info['album']
        elif video_info.get('playlist_title'):
            metadata.album = video_info['playlist_title']
        
        # Genre from categories
        if video_info.get('categories'):
            categories = video_info['categories']
            if isinstance(categories, list) and categories:
                metadata.genre = categories[0]
            elif isinstance(categories, str):
                metadata.genre = categories
        
        # Additional metadata
        metadata.publisher = video_info.get('uploader', '')
        metadata.copyright = f"© {metadata.year} {metadata.artist}" if metadata.year else f"© {metadata.artist}"
        metadata.comment = f"Downloaded from YouTube: {video_info.get('channel_url', '')}"
        
        # Language
        if video_info.get('language'):
            metadata.language = video_info['language']
        
        # Rating (if available)
        if video_info.get('average_rating'):
            metadata.rating = float(video_info['average_rating']) / 5.0 * 100
        
        # Media type detection
        if video_info.get('categories'):
            if any(cat in str(video_info['categories']).lower() for cat in ['music', 'song']):
                metadata.media_type = 'Music'
        
        return metadata

class ModernTagManager:
    """Advanced audio tagging with rich metadata support"""
    
    @staticmethod
    def tag_audio_file(audio_path: str, metadata: AudioMetadata, cover_art: bytes = None):
        """Tag audio file with rich metadata"""
        try:
            from mutagen import File
            from mutagen.id3 import ID3, APIC, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, TCON, TCOM, TCOP, TENC, TLAN, TPE3, TPE4
            
            ext = os.path.splitext(audio_path)[1].lower()
            
            if ext == '.mp3':
                try:
                    audio = ID3(audio_path)
                except:
                    audio = ID3()
                
                audio.add(TIT2(encoding=3, text=metadata.title))
                audio.add(TPE1(encoding=3, text=metadata.artist))
                audio.add(TPE2(encoding=3, text=metadata.album_artist))
                audio.add(TALB(encoding=3, text=metadata.album))
                audio.add(TDRC(encoding=3, text=metadata.year))
                
                if metadata.genre:
                    audio.add(TCON(encoding=3, text=metadata.genre))
                if metadata.composer:
                    audio.add(TCOM(encoding=3, text=metadata.composer))
                if metadata.copyright:
                    audio.add(TCOP(encoding=3, text=metadata.copyright))
                if metadata.language:
                    audio.add(TLAN(encoding=3, text=metadata.language))
                
                if metadata.track_number > 0:
                    audio.add(TRCK(encoding=3, text=f"{metadata.track_number}/{metadata.track_total or 0}"))
                
                if metadata.comment:
                    from mutagen.id3 import COMM
                    audio.add(COMM(encoding=3, lang='eng', desc='comment', text=metadata.comment))
                
                if cover_art:
                    audio.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,
                        desc='Cover',
                        data=cover_art
                    ))
                
                audio.save()
                print(f"{colors.GREEN}[✓] Audio tagged successfully with rich metadata{colors.RESET}")
                
            elif ext in ['.m4a', '.aac']:
                from mutagen.mp4 import MP4, MP4Cover
                audio = MP4(audio_path)
                
                tag_map = {
                    '\xa9nam': metadata.title,
                    '\xa9ART': metadata.artist,
                    '\xa9alb': metadata.album,
                    '\xa9day': metadata.year,
                    '\xa9gen': metadata.genre,
                    '\xa9wrt': metadata.composer,
                    'cprt': metadata.copyright,
                }
                
                for tag, value in tag_map.items():
                    if value:
                        audio[tag] = value
                
                if cover_art:
                    audio['covr'] = [MP4Cover(cover_art, MP4Cover.FORMAT_JPEG)]
                
                audio.save()
                print(f"{colors.GREEN}[✓] Audio tagged successfully with rich metadata{colors.RESET}")
                
            else:
                ModernTagManager._tag_basic(audio_path, metadata)
                
            return True
            
        except ImportError:
            print(f"{colors.YELLOW}[!] Mutagen library not installed, using basic tagging{colors.RESET}")
            ModernTagManager._tag_basic(audio_path, metadata)
            return True
        except Exception as e:
            print(f"{colors.YELLOW}[!] Advanced tagging failed: {e}{colors.RESET}")
            ModernTagManager._tag_basic(audio_path, metadata)
            return False
    
    @staticmethod
    def _tag_basic(audio_path: str, metadata: AudioMetadata):
        """Basic tagging fallback"""
        try:
            from mutagen.easyid3 import EasyID3
            from mutagen.mp3 import MP3
            
            try:
                audio = EasyID3(audio_path)
            except:
                audio = MP3(audio_path)
                audio.add_tags()
                audio = EasyID3(audio_path)
            
            audio['title'] = metadata.title
            audio['artist'] = metadata.artist
            audio['album'] = metadata.album
            
            if metadata.year:
                audio['date'] = metadata.year
                audio['year'] = metadata.year
            if metadata.genre:
                audio['genre'] = metadata.genre
            if metadata.comment:
                audio['comments'] = metadata.comment
            
            audio.save()
            print(f"{colors.GREEN}[✓] Basic tagging completed{colors.RESET}")
            
        except Exception as e:
            print(f"{colors.RED}[!] Basic tagging failed: {e}{colors.RESET}")

class UpdateChecker:
    @staticmethod
    def check():
        try:
            import requests
            print(f"{colors.BLUE}[*] Checking for updates...{colors.RESET}")
            print(f"{colors.GREEN}[+] You have the latest version{colors.RESET}")
            return True
        except:
            print(f"{colors.YELLOW}[!] Could not check for updates{colors.RESET}")
            return False

# ============================================================
# BASE YOUTUBE PLAYER CLASS
# ============================================================
class YouTubePlayer:
    """Base YouTube Player with core functionality"""
    def __init__(self):
        self.base_url = "https://www.youtube.com"
        self.config = Config()
        colors.apply_theme(self.config.get('theme', 'dark'))
        self.session = None
        self.history_file = Path("config/history.json")
        self.current_process = None
        self.is_paused = False
        self.current_results = []
        self.current_video_info = {}
        self.setup_directories()
        self.setup_signal_handlers()
        self.setup_requests()

    def setup_requests(self):
        try:
            import requests
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
        except:
            self.session = None

    def setup_directories(self):
        Path("config").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        if not self.history_file.exists():
            with open(self.history_file, 'w') as f:
                json.dump({"search_history": [], "watch_history": []}, f)

    def setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self.handle_interrupt)
        signal.signal(signal.SIGTERM, self.handle_interrupt)

    def handle_interrupt(self, signum, frame):
        print(f"\n{colors.YELLOW}[!] Application terminated by user{colors.RESET}")
        if self.current_process:
            self.current_process.terminate()
        sys.exit(0)

    def get_video_info(self, video_url):
        """Extract video metadata for tagging"""
        try:
            cmd = ['yt-dlp', '--dump-json', video_url]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                info = json.loads(result.stdout)
                self.current_video_info = {
                    'title': info.get('title', 'Unknown'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', ''),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'channel_id': info.get('channel_id', ''),
                    'channel_url': info.get('channel_url', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'categories': info.get('categories', []),
                    'tags': info.get('tags', [])
                }
                return self.current_video_info
            return None
        except Exception as e:
            print(f"{colors.RED}[!] Failed to get video info: {e}{colors.RESET}")
            return None

    def search_youtube(self, query):
        try:
            cmd = ['yt-dlp', '--flat-playlist', f'ytsearch20:{query}', '-j']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"{colors.RED}[!] Search failed{colors.RESET}")
                return None
                
            videos = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            self.current_results = [{
                'title': v['title'],
                'video_id': v['id'],
                'duration': str(v.get('duration', 'N/A')),
                'views': str(v.get('view_count', 'N/A')),
                'url': v['webpage_url']
            } for v in videos]
            
            return self.current_results
            
        except Exception as e:
            print(f"{colors.RED}[!] Search error: {e}{colors.RESET}")
            return None

    def play_video(self, video_url, audio_only=False, quality=None):
        try:
            if self.current_process:
                self.current_process.terminate()
            
            cmd = ['mpv', '--no-terminal', '--input-ipc-server=/tmp/mpvsocket']
            
            if audio_only:
                cmd.append('--no-video')
            
            if quality:
                cmd.extend(['--ytdl-format', f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'])
            else:
                cmd.append('--ytdl-format=best')
            
            cmd.append(video_url)
            
            print(f"\n{colors.GREEN}[+] Playing media... (Press 'p' to pause, 'q' to stop, 'i' for info){colors.RESET}")
            self.current_process = subprocess.Popen(cmd)
            self.add_to_history(video_url)
            self.monitor_playback()
            return True
            
        except Exception as e:
            print(f"{colors.RED}[!] Playback error: {e}{colors.RESET}")
            return False

    def monitor_playback(self):
        while True:
            try:
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    key = sys.stdin.read(1).lower()
                    if key == 'p':
                        self.toggle_pause()
                    elif key == 'q':
                        if self.current_process:
                            self.current_process.terminate()
                        return
                    elif key == 'i':
                        self.show_video_info()
                        
                if self.current_process.poll() is not None:
                    break
                    
            except (KeyboardInterrupt, Exception):
                if self.current_process:
                    self.current_process.terminate()
                break

    def toggle_pause(self):
        try:
            subprocess.run(['echo', 'cycle pause', '>', '/tmp/mpvsocket'], shell=True)
            self.is_paused = not self.is_paused
            status = "Paused" if self.is_paused else "Resumed"
            print(f"\n{colors.YELLOW}[!] {status} playback{colors.RESET}")
        except Exception as e:
            print(f"{colors.RED}[!] Pause error: {e}{colors.RESET}")

    def show_video_info(self):
        if self.current_video_info:
            print(f"\n{colors.BOLD}{colors.CYAN}VIDEO INFORMATION:{colors.RESET}")
            print(f"{colors.GREEN}Title:{colors.RESET} {self.current_video_info.get('title', 'N/A')}")
            print(f"{colors.GREEN}Uploader:{colors.RESET} {self.current_video_info.get('uploader', 'N/A')}")
            print(f"{colors.GREEN}Duration:{colors.RESET} {self.current_video_info.get('duration', 'N/A')} seconds")
            print(f"{colors.GREEN}Views:{colors.RESET} {self.current_video_info.get('view_count', 'N/A')}")
            print(f"{colors.GREEN}Likes:{colors.RESET} {self.current_video_info.get('like_count', 'N/A')}")
            if self.current_video_info.get('categories'):
                print(f"{colors.GREEN}Categories:{colors.RESET} {', '.join(self.current_video_info['categories'])}")
            if self.current_video_info.get('tags'):
                print(f"{colors.GREEN}Tags:{colors.RESET} {', '.join(self.current_video_info['tags'][:5])}")
        else:
            print(f"{colors.YELLOW}[!] No video information available{colors.RESET}")

    def add_to_history(self, video_url):
        try:
            with open(self.history_file, 'r+') as f:
                history = json.load(f)
                history['watch_history'].insert(0, {
                    'url': video_url,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                history['watch_history'] = history['watch_history'][:self.config.get('max_history', 50)]
                f.seek(0)
                json.dump(history, f, indent=4)
        except Exception as e:
            print(f"{colors.RED}[!] Failed to save history: {e}{colors.RESET}")

    def display_search_results(self, results):
        print(f"\n{colors.BOLD}SEARCH RESULTS:{colors.RESET}")
        for i, result in enumerate(results, 1):
            print(f"{colors.GREEN}{i}.{colors.RESET} {result['title']}")
            print(f"   {colors.YELLOW}Duration: {result['duration']} | Views: {result['views']}{colors.RESET}")
            print(f"   {colors.CYAN}URL: {result['url']}{colors.RESET}")

    def search_menu(self):
        while True:
            query = input(f"\n{colors.BLUE}Enter search query (or 'b' to go back): {colors.RESET}")
            if query.lower() == 'b':
                return
                
            results = self.search_youtube(query)
            if not results:
                print(f"{colors.RED}[!] No results found{colors.RESET}")
                continue
                
            self.display_search_results(results)
            self.handle_search_actions()

    def handle_search_actions(self):
        while True:
            print(f"\n{colors.BLUE}Options:{colors.RESET}")
            print(f"  {colors.GREEN}<number>{colors.RESET} - Play video")
            print(f"  {colors.GREEN}a<number>{colors.RESET} - Download audio")
            print(f"  {colors.GREEN}v<number>{colors.RESET} - Download video")
            print(f"  {colors.GREEN}b{colors.RESET} - Go back")
            print(f"\n{colors.YELLOW}Enter choice: {colors.RESET}")
            
            choice = input().strip().lower()
            
            if choice == 'b':
                return
            elif choice.startswith('a') and choice[1:].isdigit():
                video_num = int(choice[1:])
                if 1 <= video_num <= len(self.current_results):
                    print(f"{colors.YELLOW}[!] Use enhanced download from main menu{colors.RESET}")
            elif choice.startswith('v') and choice[1:].isdigit():
                video_num = int(choice[1:])
                if 1 <= video_num <= len(self.current_results):
                    print(f"{colors.YELLOW}[!] Use enhanced download from main menu{colors.RESET}")
            elif choice.isdigit():
                video_num = int(choice)
                if 1 <= video_num <= len(self.current_results):
                    self.play_video(self.current_results[video_num-1]['url'])
                    self.display_search_results(self.current_results)
            else:
                print(f"{colors.RED}[!] Invalid input{colors.RESET}")

    def url_play_menu(self):
        while True:
            url = input(f"\n{colors.BLUE}Enter YouTube URL (or 'b' to go back): {colors.RESET}")
            if url.lower() == 'b':
                return
            if 'youtube.com/watch?v=' in url or 'youtu.be/' in url:
                self.play_video(url)
            else:
                print(f"{colors.RED}[!] Invalid YouTube URL{colors.RESET}")

    def history_menu(self):
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
                
            if not history['watch_history']:
                print(f"{colors.YELLOW}[!] No history found{colors.RESET}")
                return
                
            print(f"\n{colors.BOLD}RECENTLY WATCHED:{colors.RESET}")
            for i, item in enumerate(history['watch_history'][:10], 1):
                print(f"{colors.GREEN}{i}.{colors.RESET} {item['url']}")
                print(f"   {colors.YELLOW}Time: {item['timestamp']}{colors.RESET}")
                
            while True:
                print(f"\n{colors.BLUE}Enter video number to play, or 'b' to go back: {colors.RESET}")
                choice = input().strip().lower()
                if choice == 'b':
                    return
                elif choice.isdigit():
                    video_num = int(choice)
                    if 1 <= video_num <= min(10, len(history['watch_history'])):
                        self.play_video(history['watch_history'][video_num-1]['url'])
                else:
                    print(f"{colors.RED}[!] Invalid input{colors.RESET}")
        except Exception as e:
            print(f"{colors.RED}[!] Failed to load history: {e}{colors.RESET}")

    def settings_menu(self):
        while True:
            print(f"\n{colors.BOLD}{colors.CYAN}SETTINGS{colors.RESET}")
            print(f"{colors.GREEN}1.{colors.RESET} Theme: {self.config.get('theme', 'dark')}")
            print(f"{colors.GREEN}2.{colors.RESET} Video Quality: {self.config.get('video_quality', 'best')}")
            print(f"{colors.GREEN}3.{colors.RESET} Audio Quality: {self.config.get('audio_quality', '192')}kbps")
            print(f"{colors.GREEN}4.{colors.RESET} Audio Format: {self.config.get('audio_format', 'mp3')}")
            print(f"{colors.GREEN}5.{colors.RESET} Video Format: {self.config.get('video_format', 'mp4')}")
            print(f"{colors.GREEN}6.{colors.RESET} Download Path: {self.config.get('download_path')}")
            print(f"{colors.GREEN}7.{colors.RESET} Auto Organize: {self.config.get('auto_organize', True)}")
            print(f"{colors.GREEN}8.{colors.RESET} Max History: {self.config.get('max_history', 50)}")
            print(f"{colors.GREEN}9.{colors.RESET} Back to Main Menu")
            
            choice = input(f"\n{colors.YELLOW}Select option (1-9): {colors.RESET}")
            
            if choice == '1':
                theme = input(f"{colors.BLUE}Theme (dark/light/hacker/neon): {colors.RESET}").strip().lower()
                if theme in ['dark', 'light', 'hacker', 'neon']:
                    self.config.set('theme', theme)
                    colors.apply_theme(theme)
                    print(f"{colors.GREEN}[+] Theme updated{colors.RESET}")
            elif choice == '2':
                quality = input(f"{colors.BLUE}Quality (best/1080p/720p/480p/360p): {colors.RESET}").strip()
                if quality in ['best', '1080p', '720p', '480p', '360p']:
                    self.config.set('video_quality', quality)
            elif choice == '3':
                quality = input(f"{colors.BLUE}Audio quality (128/192/256/320): {colors.RESET}").strip()
                if quality in ['128', '192', '256', '320']:
                    self.config.set('audio_quality', quality)
            elif choice == '4':
                fmt = input(f"{colors.BLUE}Audio format (mp3/m4a/aac/opus): {colors.RESET}").strip().lower()
                if fmt in ['mp3', 'm4a', 'aac', 'opus']:
                    self.config.set('audio_format', fmt)
            elif choice == '5':
                fmt = input(f"{colors.BLUE}Video format (mp4/mkv/webm): {colors.RESET}").strip().lower()
                if fmt in ['mp4', 'mkv', 'webm']:
                    self.config.set('video_format', fmt)
            elif choice == '6':
                path = input(f"{colors.BLUE}Download path: {colors.RESET}").strip()
                if path:
                    self.config.set('download_path', path)
            elif choice == '7':
                current = self.config.get('auto_organize', True)
                val = input(f"{colors.BLUE}Auto organize (true/false): {colors.RESET}").strip().lower()
                if val in ['true', 'false']:
                    self.config.set('auto_organize', val == 'true')
            elif choice == '8':
                val = input(f"{colors.BLUE}Max history entries: {colors.RESET}").strip()
                if val.isdigit():
                    self.config.set('max_history', int(val))
            elif choice == '9':
                return
            else:
                print(f"{colors.RED}[!] Invalid choice{colors.RESET}")

# ============================================================
# ENHANCED DOWNLOAD MANAGER
# ============================================================
class EnhancedDownloadManager:
    """Enhanced download manager with rich features"""
    
    def __init__(self, player):
        self.player = player
        self.config = player.config
        self.active_downloads = []
        self.download_queue = []
        self.lock = threading.Lock()
        self.metadata_extractor = MetadataExtractor()
        self.tag_manager = ModernTagManager()
        self.completed_downloads = []
        self.failed_downloads = []
    
    def download_audio_enhanced(self, url: str, format: str = 'mp3', quality: str = '192') -> bool:
        """Enhanced audio download with rich metadata"""
        try:
            video_info = self.player.get_video_info(url)
            if not video_info:
                print(f"{colors.RED}[!] Could not retrieve video information{colors.RESET}")
                return False
            
            metadata = self.metadata_extractor.extract_full_metadata(video_info)
            audio_dir = self._get_download_path('audio')
            safe_title = self._sanitize_filename(metadata.title)
            filename = f"{safe_title}.{format}"
            filepath = self._get_unique_filename(audio_dir, filename)
            
            print(f"\n{colors.GREEN}[+] Downloading: {metadata.title}{colors.RESET}")
            print(f"{colors.CYAN}[+] Artist: {metadata.artist}{colors.RESET}")
            print(f"{colors.CYAN}[+] Album: {metadata.album}{colors.RESET}")
            
            cmd = [
                'yt-dlp', '-x',
                '--audio-format', format,
                '--audio-quality', quality,
                '-o', str(filepath),
                '--progress',
                '--newline',
                url
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            total_size = 0
            for line in process.stdout:
                if '[download]' in line:
                    if 'Destination' in line:
                        continue
                    size_match = re.search(r'(\d+\.\d+)(\w+)B', line)
                    if size_match and '100%' not in line:
                        value = float(size_match.group(1))
                        unit = size_match.group(2)
                        total_size = self._parse_size(value, unit)
                    
                    if '%' in line:
                        match = re.search(r'(\d+\.\d+)%', line)
                        if match:
                            percent = float(match.group(1))
                            downloaded = int((percent / 100) * total_size) if total_size > 0 else 0
                            if downloaded > 0:
                                print(f'\r  Progress: {percent:.1f}%  ({self._format_size(downloaded)}/{self._format_size(total_size)})', end='')
            
            process.wait()
            
            if process.returncode == 0 and filepath.exists():
                cover_art = None
                if video_info.get('thumbnail'):
                    cover_art = self._download_cover_art(video_info['thumbnail'])
                
                self.tag_manager.tag_audio_file(str(filepath), metadata, cover_art)
                self.completed_downloads.append(str(filepath))
                print(f"\n{colors.GREEN}[✓] Audio download completed: {filepath.name}{colors.RESET}")
                return True
            else:
                print(f"{colors.RED}[!] Download failed{colors.RESET}")
                return False
                
        except Exception as e:
            print(f"{colors.RED}[!] Audio download failed: {e}{colors.RESET}")
            return False
    
    def download_video_enhanced(self, url: str, quality: str = 'best', format: str = 'mp4') -> bool:
        """Enhanced video download with quality selection"""
        try:
            quality_map = {
                '144p': 'bestvideo[height<=144]+bestaudio/best[height<=144]',
                '240p': 'bestvideo[height<=240]+bestaudio/best[height<=240]',
                '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
                '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
                '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
                '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                '1440p': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
                '2160p': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
                '4320p': 'bestvideo[height<=4320]+bestaudio/best[height<=4320]',
                'best': 'bestvideo+bestaudio/best'
            }
            
            format_selector = quality_map.get(quality, 'best')
            video_dir = self._get_download_path('video')
            
            video_info = self.player.get_video_info(url)
            safe_title = self._sanitize_filename(video_info.get('title', 'video')) if video_info else 'video'
            filename = f"{safe_title}.{format}"
            filepath = self._get_unique_filename(video_dir, filename)
            
            print(f"\n{colors.GREEN}[+] Downloading video: {safe_title}{colors.RESET}")
            print(f"{colors.CYAN}[+] Quality: {quality}{colors.RESET}")
            
            cmd = [
                'yt-dlp',
                '-f', format_selector,
                '--merge-output-format', format,
                '-o', str(filepath),
                '--progress',
                '--newline',
                url
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            total_size = 0
            for line in process.stdout:
                if '[download]' in line:
                    if 'Destination' in line:
                        continue
                    size_match = re.search(r'(\d+\.\d+)(\w+)B', line)
                    if size_match and '100%' not in line:
                        value = float(size_match.group(1))
                        unit = size_match.group(2)
                        total_size = self._parse_size(value, unit)
                    
                    if '%' in line:
                        match = re.search(r'(\d+\.\d+)%', line)
                        if match:
                            percent = float(match.group(1))
                            downloaded = int((percent / 100) * total_size) if total_size > 0 else 0
                            if downloaded > 0:
                                print(f'\r  Progress: {percent:.1f}%  ({self._format_size(downloaded)}/{self._format_size(total_size)})', end='')
            
            process.wait()
            
            if process.returncode == 0 and filepath.exists():
                self.completed_downloads.append(str(filepath))
                print(f"\n{colors.GREEN}[✓] Video download completed: {filepath.name}{colors.RESET}")
                return True
            else:
                print(f"{colors.RED}[!] Download failed{colors.RESET}")
                return False
                
        except Exception as e:
            print(f"{colors.RED}[!] Video download failed: {e}{colors.RESET}")
            return False
    
    def batch_download(self, urls: List[str], media_type: str = 'audio'):
        """Batch download multiple videos"""
        total = len(urls)
        success = 0
        
        print(f"\n{colors.BOLD}{colors.CYAN}BATCH DOWNLOAD STARTED{colors.RESET}")
        print(f"{colors.YELLOW}Total items: {total}{colors.RESET}")
        
        for i, url in enumerate(urls, 1):
            print(f"\n{colors.BLUE}[{i}/{total}] Processing...{colors.RESET}")
            
            if media_type == 'audio':
                if self.download_audio_enhanced(url):
                    success += 1
            else:
                if self.download_video_enhanced(url):
                    success += 1
        
        print(f"\n{colors.GREEN}[✓] Batch download completed: {success}/{total} successful{colors.RESET}")
        return success
    
    def _get_download_path(self, media_type: str) -> Path:
        base_path = Path(self.config.get('download_path'))
        media_type_path = base_path / ('Videos' if media_type == 'video' else 'Audios')
        
        if self.config.get('auto_organize'):
            date_path = datetime.now().strftime('%Y/%m')
            media_type_path = media_type_path / date_path
        
        media_type_path.mkdir(parents=True, exist_ok=True)
        return media_type_path
    
    def _sanitize_filename(self, filename: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        if len(filename) > 200:
            filename = filename[:200]
        return filename.strip()
    
    def _get_unique_filename(self, directory: Path, filename: str) -> Path:
        filepath = directory / filename
        if not filepath.exists():
            return filepath
        
        name = filepath.stem
        ext = filepath.suffix
        counter = 1
        
        dup_match = re.search(r'_\((\d+)\)$', name)
        if dup_match:
            base_name = name[:dup_match.start()]
            counter = int(dup_match.group(1)) + 1
        else:
            base_name = name
        
        while True:
            new_name = f"{base_name}_({counter}){ext}"
            new_path = directory / new_name
            if not new_path.exists():
                return new_path
            counter += 1
    
    def _parse_size(self, value: float, unit: str) -> int:
        units = {'B': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3}
        return int(value * units.get(unit, 1))
    
    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f}{unit}'
            size /= 1024
        return f'{size:.1f}TB'
    
    def _download_cover_art(self, thumbnail_url: str) -> bytes:
        try:
            if self.player.session:
                response = self.player.session.get(thumbnail_url)
                if response.status_code == 200:
                    return response.content
            return None
        except:
            return None
    
    def open_download_folder(self):
        """Open the downloads folder in file manager"""
        try:
            path = Path(self.config.get('download_path'))
            if platform.system() == 'Windows':
                os.startfile(path)
            elif platform.system() == 'Darwin':
                subprocess.run(['open', str(path)])
            else:
                subprocess.run(['xdg-open', str(path)])
            print(f"{colors.GREEN}[✓] Opening download folder...{colors.RESET}")
        except Exception as e:
            print(f"{colors.RED}[!] Failed to open folder: {e}{colors.RESET}")
    
    def delete_file(self, filepath: Path) -> bool:
        try:
            if filepath.exists():
                filepath.unlink()
                print(f"{colors.GREEN}[✓] Deleted: {filepath.name}{colors.RESET}")
                return True
            else:
                print(f"{colors.YELLOW}[!] File not found{colors.RESET}")
                return False
        except Exception as e:
            print(f"{colors.RED}[!] Delete failed: {e}{colors.RESET}")
            return False

# ============================================================
# MODERN YOUTUBE PLAYER - ENHANCED VERSION
# ============================================================
class ModernYouTubePlayer(YouTubePlayer):
    """Enhanced version with all modern features"""
    
    def __init__(self):
        super().__init__()
        self.enhanced_downloader = EnhancedDownloadManager(self)
        self.stats = {
            'total_downloads': 0,
            'total_size': 0,
            'download_speed': 0,
            'active_downloads': 0
        }
        if RICH_AVAILABLE:
            self.console = Console()
    
    def show_modern_main_menu(self):
        """Enhanced main menu with more options"""
        while True:
            if RICH_AVAILABLE:
                self._show_rich_menu()
            else:
                self._show_legacy_menu()
            
            try:
                choice = input(f"\n{colors.YELLOW}Select option: {colors.RESET}")
                
                if choice == '1':
                    self.search_menu()
                elif choice == '2':
                    self.url_play_menu()
                elif choice == '3':
                    self.enhanced_download_menu()
                elif choice == '4':
                    self.batch_download_menu()
                elif choice == '5':
                    self.download_playlist_menu()
                elif choice == '6':
                    self.subtitle_download_menu()
                elif choice == '7':
                    self.thumbnail_download_menu()
                elif choice == '8':
                    self.file_management_menu()
                elif choice == '9':
                    self.settings_menu()
                elif choice == '10':
                    self.history_menu()
                elif choice == '11':
                    self.stats_menu()
                elif choice == '12':
                    self.cleanup_menu()
                elif choice == '13':
                    UpdateChecker.check()
                elif choice == '14':
                    print(f"\n{colors.GREEN}[+] Exiting...{colors.RESET}")
                    sys.exit(0)
                else:
                    print(f"{colors.RED}[!] Invalid choice{colors.RESET}")
                    
            except KeyboardInterrupt:
                print(f"\n{colors.YELLOW}[!] Operation cancelled{colors.RESET}")
    
    def _show_rich_menu(self):
        """Display menu using rich library"""
        table = Table(title="TerXTubE2 - Main Menu", title_style="bold cyan")
        table.add_column("Option", style="bold green", width=6)
        table.add_column("Feature", style="white")
        
        menu_items = [
            ("1", "Search & Play Videos"),
            ("2", "Play with URL"),
            ("3", "Enhanced Audio Download (with rich tags)"),
            ("4", "Batch Download"),
            ("5", "Download Playlist"),
            ("6", "Download Subtitles"),
            ("7", "Download Thumbnail"),
            ("8", "File Management"),
            ("9", "Settings"),
            ("10", "History"),
            ("11", "Download Statistics"),
            ("12", "Cleanup & Optimization"),
            ("13", "Check for Updates"),
            ("14", "Exit")
        ]
        
        for num, feature in menu_items:
            table.add_row(num, feature)
        
        self.console.print(table)
    
    def _show_legacy_menu(self):
        """Fallback menu for non-rich environments"""
        print(f"\n{colors.BOLD}{colors.CYAN}MAIN MENU{colors.RESET}")
        print(f"{colors.GREEN}1.{colors.RESET} Search and Play")
        print(f"{colors.GREEN}2.{colors.RESET} Play with URL")
        print(f"{colors.GREEN}3.{colors.RESET} Enhanced Audio Download")
        print(f"{colors.GREEN}4.{colors.RESET} Batch Download")
        print(f"{colors.GREEN}5.{colors.RESET} Download Playlist")
        print(f"{colors.GREEN}6.{colors.RESET} Download Subtitles")
        print(f"{colors.GREEN}7.{colors.RESET} Download Thumbnail")
        print(f"{colors.GREEN}8.{colors.RESET} File Management")
        print(f"{colors.GREEN}9.{colors.RESET} Settings")
        print(f"{colors.GREEN}10.{colors.RESET} History")
        print(f"{colors.GREEN}11.{colors.RESET} Statistics")
        print(f"{colors.GREEN}12.{colors.RESET} Cleanup")
        print(f"{colors.GREEN}13.{colors.RESET} Check Updates")
        print(f"{colors.GREEN}14.{colors.RESET} Exit")
    
    def enhanced_download_menu(self):
        """Enhanced audio download with rich metadata"""
        print(f"\n{colors.BOLD}{colors.CYAN}ENHANCED AUDIO DOWNLOAD{colors.RESET}")
        print(f"{colors.GREEN}1.{colors.RESET} Download from URL (with rich tags)")
        print(f"{colors.GREEN}2.{colors.RESET} Download from search results")
        print(f"{colors.GREEN}3.{colors.RESET} Back")
        
        choice = input(f"\n{colors.YELLOW}Select option: {colors.RESET}")
        
        if choice == '1':
            url = input(f"\n{colors.BLUE}Enter YouTube URL: {colors.RESET}")
            if 'youtube.com/watch?v=' in url or 'youtu.be/' in url:
                fmt = input(f"{colors.BLUE}Format (mp3/m4a/aac/opus) [mp3]: {colors.RESET}") or 'mp3'
                quality = input(f"{colors.BLUE}Quality (128/192/256/320) [192]: {colors.RESET}") or '192'
                self.enhanced_downloader.download_audio_enhanced(url, fmt, quality)
            else:
                print(f"{colors.RED}[!] Invalid URL{colors.RESET}")
        elif choice == '2':
            query = input(f"\n{colors.BLUE}Search query: {colors.RESET}")
            results = self.search_youtube(query)
            if results:
                self.display_search_results(results)
                print(f"\n{colors.BLUE}Enter video number to download: {colors.RESET}")
                num = input().strip()
                if num.isdigit() and 1 <= int(num) <= len(results):
                    self.enhanced_downloader.download_audio_enhanced(results[int(num)-1]['url'])
        elif choice == '3':
            return
    
    def batch_download_menu(self):
        """Batch download multiple videos"""
        print(f"\n{colors.BOLD}{colors.CYAN}BATCH DOWNLOAD{colors.RESET}")
        print(f"{colors.GREEN}1.{colors.RESET} Download from URL list")
        print(f"{colors.GREEN}2.{colors.RESET} Download from search results")
        print(f"{colors.GREEN}3.{colors.RESET} Back")
        
        choice = input(f"\n{colors.YELLOW}Select option: {colors.RESET}")
        
        if choice == '1':
            urls = []
            print(f"{colors.BLUE}Enter URLs (one per line, empty line to finish):{colors.RESET}")
            while True:
                url = input().strip()
                if not url:
                    break
                if 'youtube.com' in url or 'youtu.be' in url:
                    urls.append(url)
                else:
                    print(f"{colors.YELLOW}[!] Skipping invalid URL{colors.RESET}")
            
            if urls:
                media_type = input(f"{colors.BLUE}Type (audio/video) [audio]: {colors.RESET}") or 'audio'
                self.enhanced_downloader.batch_download(urls, media_type)
        
        elif choice == '2':
            query = input(f"\n{colors.BLUE}Search query: {colors.RESET}")
            results = self.search_youtube(query)
            if results:
                self.display_search_results(results)
                print(f"\n{colors.BLUE}Enter video numbers (comma separated): {colors.RESET}")
                nums = input().strip()
                try:
                    indices = [int(x.strip()) for x in nums.split(',') if x.strip()]
                    urls = [results[i-1]['url'] for i in indices if 1 <= i <= len(results)]
                    if urls:
                        media_type = input(f"{colors.BLUE}Type (audio/video) [audio]: {colors.RESET}") or 'audio'
                        self.enhanced_downloader.batch_download(urls, media_type)
                except:
                    print(f"{colors.RED}[!] Invalid input{colors.RESET}")
        
        elif choice == '3':
            return
    
    def download_playlist_menu(self):
        """Download playlist"""
        print(f"\n{colors.BOLD}{colors.CYAN}DOWNLOAD PLAYLIST{colors.RESET}")
        url = input(f"{colors.BLUE}Enter playlist URL: {colors.RESET}")
        if 'youtube.com/playlist' in url:
            media_type = input(f"{colors.BLUE}Type (audio/video) [audio]: {colors.RESET}") or 'audio'
            
            # Get playlist videos
            try:
                cmd = ['yt-dlp', '--flat-playlist', '--dump-json', url]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    entries = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
                    urls = [f"https://youtube.com/watch?v={e['id']}" for e in entries]
                    print(f"{colors.GREEN}[+] Found {len(urls)} videos{colors.RESET}")
                    self.enhanced_downloader.batch_download(urls, media_type)
                else:
                    print(f"{colors.RED}[!] Failed to get playlist{colors.RESET}")
            except Exception as e:
                print(f"{colors.RED}[!] Error: {e}{colors.RESET}")
        else:
            print(f"{colors.RED}[!] Invalid playlist URL{colors.RESET}")
    
    def subtitle_download_menu(self):
        """Download subtitles"""
        print(f"\n{colors.BOLD}{colors.CYAN}DOWNLOAD SUBTITLES{colors.RESET}")
        url = input(f"{colors.BLUE}Enter YouTube URL: {colors.RESET}")
        lang = input(f"{colors.BLUE}Language (default: en): {colors.RESET}") or 'en'
        
        try:
            cmd = ['yt-dlp', '--write-subs', '--sub-lang', lang, '--skip-download', url]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"{colors.GREEN}[✓] Subtitles downloaded{colors.RESET}")
            else:
                print(f"{colors.YELLOW}[!] No subtitles available{colors.RESET}")
        except Exception as e:
            print(f"{colors.RED}[!] Failed: {e}{colors.RESET}")
    
    def thumbnail_download_menu(self):
        """Download thumbnail"""
        print(f"\n{colors.BOLD}{colors.CYAN}DOWNLOAD THUMBNAIL{colors.RESET}")
        url = input(f"{colors.BLUE}Enter YouTube URL: {colors.RESET}")
        
        try:
            video_info = self.get_video_info(url)
            if video_info and video_info.get('thumbnail'):
                import requests
                response = requests.get(video_info['thumbnail'])
                if response.status_code == 200:
                    safe_title = self.enhanced_downloader._sanitize_filename(video_info.get('title', 'thumbnail'))
                    path = self.enhanced_downloader._get_download_path('video') / f"{safe_title}_thumb.jpg"
                    with open(path, 'wb') as f:
                        f.write(response.content)
                    print(f"{colors.GREEN}[✓] Thumbnail saved: {path.name}{colors.RESET}")
                else:
                    print(f"{colors.RED}[!] Failed to download{colors.RESET}")
            else:
                print(f"{colors.YELLOW}[!] No thumbnail available{colors.RESET}")
        except Exception as e:
            print(f"{colors.RED}[!] Failed: {e}{colors.RESET}")
    
    def file_management_menu(self):
        """File management menu"""
        while True:
            print(f"\n{colors.BOLD}{colors.CYAN}FILE MANAGEMENT{colors.RESET}")
            print(f"{colors.GREEN}1.{colors.RESET} Open Download Folder")
            print(f"{colors.GREEN}2.{colors.RESET} Delete File")
            print(f"{colors.GREEN}3.{colors.RESET} List Downloaded Files")
            print(f"{colors.GREEN}4.{colors.RESET} Back")
            
            choice = input(f"\n{colors.YELLOW}Select option: {colors.RESET}")
            
            if choice == '1':
                self.enhanced_downloader.open_download_folder()
            elif choice == '2':
                self._delete_file_menu()
            elif choice == '3':
                self._list_downloaded_files()
            elif choice == '4':
                return
            else:
                print(f"{colors.RED}[!] Invalid choice{colors.RESET}")
    
    def _list_downloaded_files(self):
        """List all downloaded files"""
        video_dir = self.enhanced_downloader._get_download_path('video')
        audio_dir = self.enhanced_downloader._get_download_path('audio')
        
        files = []
        if video_dir.exists():
            files.extend([(f, 'Video') for f in video_dir.glob('*') if f.is_file()])
        if audio_dir.exists():
            files.extend([(f, 'Audio') for f in audio_dir.glob('*') if f.is_file()])
        
        if not files:
            print(f"{colors.YELLOW}[!] No downloaded files found{colors.RESET}")
            return
        
        print(f"\n{colors.BOLD}{colors.CYAN}DOWNLOADED FILES:{colors.RESET}")
        for i, (filepath, ftype) in enumerate(files, 1):
            size = filepath.stat().st_size
            size_str = self.enhanced_downloader._format_size(size)
            print(f"{colors.GREEN}{i}.{colors.RESET} {filepath.name}")
            print(f"   {colors.YELLOW}Type: {ftype} | Size: {size_str}{colors.RESET}")
        
        return files
    
    def _delete_file_menu(self):
        """Delete a file with selection"""
        files = self._list_downloaded_files()
        if not files:
            return
        
        num = input(f"\n{colors.BLUE}Enter file number to delete: {colors.RESET}")
        if num.isdigit() and 1 <= int(num) <= len(files):
            confirm = input(f"{colors.YELLOW}Are you sure? (y/n): {colors.RESET}")
            if confirm.lower() == 'y':
                self.enhanced_downloader.delete_file(files[int(num)-1][0])
    
    def stats_menu(self):
        """Show download statistics"""
        print(f"\n{colors.BOLD}{colors.CYAN}DOWNLOAD STATISTICS{colors.RESET}")
        print(f"{colors.GREEN}Total Downloads:{colors.RESET} {len(self.enhanced_downloader.completed_downloads)}")
        
        # Calculate total size
        total_size = 0
        for path_str in self.enhanced_downloader.completed_downloads:
            try:
                path = Path(path_str)
                if path.exists():
                    total_size += path.stat().st_size
            except:
                pass
        
        print(f"{colors.GREEN}Total Size:{colors.RESET} {self.enhanced_downloader._format_size(total_size)}")
        print(f"{colors.GREEN}Failed Downloads:{colors.RESET} {len(self.enhanced_downloader.failed_downloads)}")
        
        if self.enhanced_downloader.completed_downloads:
            print(f"\n{colors.BOLD}Recent Downloads:{colors.RESET}")
            for item in self.enhanced_downloader.completed_downloads[-5:]:
                print(f"  {colors.GREEN}✓{colors.RESET} {Path(item).name}")
    
    def cleanup_menu(self):
        """Cleanup and optimization menu"""
        print(f"\n{colors.BOLD}{colors.CYAN}CLEANUP & OPTIMIZATION{colors.RESET}")
        print(f"{colors.GREEN}1.{colors.RESET} Clear download cache")
        print(f"{colors.GREEN}2.{colors.RESET} Remove duplicate files")
        print(f"{colors.GREEN}3.{colors.RESET} Back")
        
        choice = input(f"\n{colors.YELLOW}Select option: {colors.RESET}")
        
        if choice == '1':
            cache_dir = Path.home() / '.cache' / 'yt-dlp'
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                print(f"{colors.GREEN}[✓] Cache cleared{colors.RESET}")
            else:
                print(f"{colors.YELLOW}[!] No cache found{colors.RESET}")
        
        elif choice == '2':
            self._remove_duplicates()
        
        elif choice == '3':
            return
    
    def _remove_duplicates(self):
        """Remove duplicate downloaded files"""
        video_dir = self.enhanced_downloader._get_download_path('video')
        audio_dir = self.enhanced_downloader._get_download_path('audio')
        
        duplicates = []
        for directory in [video_dir, audio_dir]:
            if directory.exists():
                files = {}
                for file in directory.glob('*'):
                    if file.is_file():
                        key = (file.stem, file.stat().st_size)
                        if key in files:
                            duplicates.append(file)
                        else:
                            files[key] = file
        
        if duplicates:
            print(f"{colors.YELLOW}Found {len(duplicates)} duplicate files{colors.RESET}")
            for dup in duplicates:
                print(f"  {colors.RED}Duplicate:{colors.RESET} {dup.name}")
                if input(f"{colors.BLUE}Delete? (y/n): {colors.RESET}").lower() == 'y':
                    dup.unlink()
                    print(f"{colors.GREEN}[✓] Deleted{colors.RESET}")
        else:
            print(f"{colors.GREEN}[✓] No duplicates found{colors.RESET}")

# ============================================================
# MAIN EXECUTION
# ============================================================
if __name__ == "__main__":
    # Check and install dependencies
    DependencyManager.check_and_install()
    
    try:
        import requests
        from bs4 import BeautifulSoup
        import mutagen
        import yt_dlp
    except ImportError:
        packages = ['requests', 'beautifulsoup4', 'yt-dlp', 'mutagen']
        if not RICH_AVAILABLE:
            packages.append('rich')
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + packages, capture_output=True)
        import requests
        from bs4 import BeautifulSoup
        import mutagen
        import yt_dlp
    
    clear_screen()
    if RICH_AVAILABLE:
        show_enhanced_banner()
    else:
        show_banner()
    
    # Start modern application
    try:
        player = ModernYouTubePlayer()
        player.show_modern_main_menu()
    except Exception as e:
        print(f"{colors.RED}[!] Fatal error: {e}{colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)