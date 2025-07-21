#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
from pathlib import Path
from urllib.parse import urlparse, quote
from datetime import datetime

# Text Styling
class colors:
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

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

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

class DependencyManager:
    @staticmethod
    def check_and_install():
        required = {
            'system': ['mpv', 'python', 'ffmpeg', 'termux-api'],
            'python': ['requests', 'beautifulsoup4', 'yt-dlp']
        }

        print(f"{colors.BLUE}[*] Checking dependencies...{colors.RESET}")
        
        # Check system packages
        missing_system = []
        for pkg in required['system']:
            if not DependencyManager._check_system_package(pkg):
                missing_system.append(pkg)
        
        # Check Python packages
        missing_python = []
        for pkg in required['python']:
            try:
                __import__(pkg.split('-')[0])
            except ImportError:
                missing_python.append(pkg)
        
        # Install missing packages
        if missing_system or missing_python:
            print(f"{colors.YELLOW}[!] Installing missing packages...{colors.RESET}")
            DependencyManager._install_packages(missing_system, missing_python)
        
        print(f"{colors.GREEN}[+] All dependencies are satisfied!{colors.RESET}")
        time.sleep(2)
        clear_screen()
        show_banner()

    @staticmethod
    def _check_system_package(pkg):
        return shutil.which(pkg) is not None

    @staticmethod
    def _install_packages(system_pkgs, python_pkgs):
        if system_pkgs:
            subprocess.run(['pkg', 'install', '-y'] + system_pkgs,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        
        if python_pkgs:
            subprocess.run([sys.executable, '-m', 'pip', 'install'] + python_pkgs,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)

class YouTubePlayer:
    def __init__(self):
        self.base_url = "https://www.youtube.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
        })
        self.history_file = Path("config/history.json")
        self.current_process = None
        self.is_paused = False
        self.current_results = []
        self.setup_directories()
        self.setup_signal_handlers()

    def setup_directories(self):
        Path("config").mkdir(exist_ok=True)
        downloads_dir = Path("/storage/emulated/0/Download") if platform.system() != "Windows" else Path.home() / "Downloads"
        self.video_dir = downloads_dir / "YouTube_Videos"
        self.audio_dir = downloads_dir / "YouTube_Audios"
        self.video_dir.mkdir(exist_ok=True, parents=True)
        self.audio_dir.mkdir(exist_ok=True, parents=True)
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

    def search_youtube(self, query):
        try:
            cmd = ['yt-dlp', '--flat-playlist', f'ytsearch10:{query}', '-j']
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
            
            print(f"\n{colors.GREEN}[+] Playing media... (Press 'p' to pause, 'q' to stop){colors.RESET}")
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
                        return  # Return to search results without exiting
                        
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

    def download_video(self, url, audio_only=False, quality=None):
        try:
            cmd = ['yt-dlp']
            
            if audio_only:
                cmd.extend(['-x', '--audio-format', 'mp3'])
                output_dir = self.audio_dir
            else:
                output_dir = self.video_dir
                if quality:
                    cmd.extend(['-f', f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'])
            
            cmd.extend(['-o', f'{output_dir}/%(title)s.%(ext)s', url])
            
            print(f"\n{colors.GREEN}[+] Downloading to {output_dir}...{colors.RESET}")
            subprocess.run(cmd, check=True)
            print(f"{colors.GREEN}[✓] Download completed!{colors.RESET}")
            return True
            
        except Exception as e:
            print(f"{colors.RED}[!] Download failed: {e}{colors.RESET}")
            return False

    def copy_to_clipboard(self, text):
        try:
            if platform.system() == 'Linux':
                subprocess.run(['termux-clipboard-set', text], check=True)
            elif platform.system() == 'Darwin':
                subprocess.run(['pbcopy'], input=text.encode(), check=True)
            elif platform.system() == 'Windows':
                subprocess.run(['clip'], input=text.encode(), check=True)
            print(f"{colors.GREEN}[✓] Copied to clipboard!{colors.RESET}")
        except Exception as e:
            print(f"{colors.RED}[!] Clipboard error: {e}{colors.RESET}")

    def add_to_history(self, video_url):
        try:
            with open(self.history_file, 'r+') as f:
                history = json.load(f)
                history['watch_history'].insert(0, {
                    'url': video_url,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                history['watch_history'] = history['watch_history'][:50]
                f.seek(0)
                json.dump(history, f, indent=4)
        except Exception as e:
            print(f"{colors.RED}[!] Failed to save history: {e}{colors.RESET}")

    def show_main_menu(self):
        while True:
            print(f"\n{colors.BOLD}{colors.CYAN}MAIN MENU{colors.RESET}")
            print(f"{colors.GREEN}1.{colors.RESET} Search and Play")
            print(f"{colors.GREEN}2.{colors.RESET} Play with URL")
            print(f"{colors.GREEN}3.{colors.RESET} View History")
            print(f"{colors.GREEN}4.{colors.RESET} Exit")
            
            try:
                choice = input(f"\n{colors.YELLOW}Select option (1-4): {colors.RESET}")
                
                if choice == '1':
                    self.search_menu()
                elif choice == '2':
                    self.url_play_menu()
                elif choice == '3':
                    self.history_menu()
                elif choice == '4':
                    print(f"\n{colors.GREEN}[+] Exiting...{colors.RESET}")
                    sys.exit(0)
                else:
                    print(f"{colors.RED}[!] Invalid choice{colors.RESET}")
                    
            except KeyboardInterrupt:
                print(f"\n{colors.YELLOW}[!] Operation cancelled{colors.RESET}")

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

    def display_search_results(self, results):
        print(f"\n{colors.BOLD}SEARCH RESULTS:{colors.RESET}")
        for i, result in enumerate(results, 1):
            print(f"{colors.GREEN}{i}.{colors.RESET} {result['title']}")
            print(f"   {colors.YELLOW}Duration: {result['duration']} | Views: {result['views']}{colors.RESET}")
            print(f"   {colors.CYAN}URL: {result['url']}{colors.RESET}")

    def handle_search_actions(self):
        while True:
            print(f"\n{colors.BLUE}Enter video number to play, 'd<number>' to download, or 'b' to go back: {colors.RESET}")
            choice = input().strip().lower()
            
            if choice == 'b':
                return
            elif choice.startswith('d') and choice[1:].isdigit():
                video_num = int(choice[1:])
                if 1 <= video_num <= len(self.current_results):
                    self.download_video(self.current_results[video_num-1]['url'])
            elif choice.isdigit():
                video_num = int(choice)
                if 1 <= video_num <= len(self.current_results):
                    self.play_video(self.current_results[video_num-1]['url'])
                    # After playback returns here
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
                print(f"\n{colors.BLUE}Enter video number to play, 'd<number>' to download, or 'b' to go back: {colors.RESET}")
                choice = input().strip().lower()
                
                if choice == 'b':
                    return
                elif choice.startswith('d') and choice[1:].isdigit():
                    video_num = int(choice[1:])
                    if 1 <= video_num <= min(10, len(history['watch_history'])):
                        self.download_video(history['watch_history'][video_num-1]['url'])
                elif choice.isdigit():
                    video_num = int(choice)
                    if 1 <= video_num <= min(10, len(history['watch_history'])):
                        self.play_video(history['watch_history'][video_num-1]['url'])
                else:
                    print(f"{colors.RED}[!] Invalid input{colors.RESET}")
                
        except Exception as e:
            print(f"{colors.RED}[!] Failed to load history: {e}{colors.RESET}")

if __name__ == "__main__":
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        DependencyManager.check_and_install()
        import requests
        from bs4 import BeautifulSoup
        
    clear_screen()
    show_banner()
    
    # Final check before starting
    DependencyManager.check_and_install()
    
    # Start application
    try:
        player = YouTubePlayer()
        player.show_main_menu()
    except Exception as e:
        print(f"{colors.RED}[!] Fatal error: {e}{colors.RESET}")
        sys.exit(1)
