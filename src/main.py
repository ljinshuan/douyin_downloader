import argparse
import asyncio
import logging
import platform
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from src.addon import DouyinAddon
from src.catalog import JsonlCatalog
from src.dedup import BloomDedup
from src.downloader import VideoDownloader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_DOWNLOAD_DIR = "downloads"
DEFAULT_PORT = 8081

_CHROME_PATHS_MACOS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
_CHROME_NAMES_LINUX = ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]


def find_chrome() -> str | None:
    system = platform.system()
    if system == "Darwin":
        for path in _CHROME_PATHS_MACOS:
            if Path(path).exists():
                return path
    for name in _CHROME_NAMES_LINUX:
        found = shutil.which(name)
        if found:
            return found
    return None


def launch_chrome(port: int) -> subprocess.Popen | None:
    chrome = find_chrome()
    if not chrome:
        logger.warning("Chrome not found, skipping browser launch")
        return None
    cmd = [
        chrome,
        f"--proxy-server=http://127.0.0.1:{port}",
        "--ignore-certificate-errors",
        f"--user-data-dir={Path.home() / '.douyin-downloader' / 'chrome'}",
        "https://www.douyin.com",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info("Chrome launched (PID %d)", proc.pid)
    return proc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Douyin video auto-downloader via mitmproxy"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="Proxy port (default: 8080)"
    )
    parser.add_argument(
        "--download-dir",
        type=str,
        default=DEFAULT_DOWNLOAD_DIR,
        help=f"Download directory (default: {DEFAULT_DOWNLOAD_DIR})",
    )
    parser.add_argument(
        "--reset-filter",
        action="store_true",
        help="Reset the bloom filter before starting",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-launch Chrome",
    )
    parser.add_argument(
        "--download-favorites",
        action="store_true",
        help="Enable downloading from favorite/liked list API",
    )
    return parser.parse_args()


async def run_proxy(port: int, download_dir: str, reset_filter: bool, no_browser: bool, download_favorites: bool = False) -> None:
    dl_dir = Path(download_dir)
    dl_dir.mkdir(parents=True, exist_ok=True)

    bloom_path = dl_dir / "bloom_filter.bin"

    if reset_filter:
        BloomDedup.reset(bloom_path)

    dedup = BloomDedup(bloom_path)
    catalog = JsonlCatalog(dl_dir / "videos.jsonl")
    downloader = VideoDownloader(dl_dir)

    addon = DouyinAddon(downloader, dedup, catalog, download_favorites=download_favorites)

    opts = Options(listen_host="127.0.0.1", listen_port=port)
    master = DumpMaster(opts)
    master.addons.add(addon)

    chrome_proc: subprocess.Popen | None = None

    def shutdown(*_args):
        nonlocal chrome_proc
        logger.info("Shutting down...")
        dedup.save()
        if chrome_proc:
            chrome_proc.terminate()
            chrome_proc = None
        master.shutdown()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except NotImplementedError:
            pass

    logger.info("Starting proxy on 127.0.0.1:%d", port)
    logger.info("Download dir: %s", dl_dir.resolve())
    if not no_browser:
        chrome_proc = launch_chrome(port)
    logger.info("Press Ctrl+C to stop")

    try:
        await master.run()
    finally:
        dedup.save()
        logger.info("Bloom filter saved. Bye!")


def main() -> None:
    args = parse_args()
    asyncio.run(run_proxy(args.port, args.download_dir, args.reset_filter, args.no_browser, args.download_favorites))


if __name__ == "__main__":
    main()
