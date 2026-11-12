"""Keeps a Bluetooth link to the LED panel and switches Kaolin's animation on events.

    pythonw kaolin_daemon.py          run (started from the Windows Startup folder)
    python  kaolin_daemon.py stop     stop it and free the panel for the phone app
    python  hook.py done|working|waiting|ready

Events come in as one UDP datagram on 127.0.0.1:47474 (sent by hook.py from Claude Code hooks).
The four animations are stored in panel slots once per connection, so switching is a
single tiny Bluetooth write instead of re-uploading a GIF.
"""
import asyncio
import hashlib
import json
import logging
import logging.handlers
import socket
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent
PORT = 47474
BUILD = ROOT / "build"

# state -> (slot, brightness)
SLOTS = {"done": (1, 80), "ready": (2, 60), "waiting": (3, 80), "working": (4, 15)}
SPIN_SECONDS = 5       # how long the staff spin plays before settling into "ready"
DIM_AFTER = 20 * 60    # "ready" dims after this long with no new event

log = logging.getLogger("kaolin")


def setup_logging():
    h = logging.handlers.RotatingFileHandler(ROOT / "kaolin_daemon.log", maxBytes=200_000, backupCount=1)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[h])


def panel_address() -> str:
    for name in ("config.toml", "config.example.toml"):
        p = ROOT / name
        if p.exists():
            addr = tomllib.loads(p.read_text(encoding="utf-8")).get("panel", {}).get("address", "")
            if addr:
                return addr
    return ""


class Panel:
    def __init__(self, address: str):
        self.address = address
        self.client = None
        self.lock = asyncio.Lock()

    def connected(self) -> bool:
        try:
            return bool(self.client and self.client._connected and self.client._session._client.is_connected)
        except Exception:
            return False

    async def ensure(self):
        if self.connected():
            return
        from pypixelcolor import AsyncClient
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
        self.client = AsyncClient(self.address)
        await asyncio.wait_for(self.client.connect(), 20)
        await self.upload_if_changed()
        log.info("connected")

    async def upload_if_changed(self, force: bool = False):
        """Slots survive power-off, so only re-upload when the GIFs changed."""
        digest = hashlib.sha1(b"".join((BUILD / f"{s}.gif").read_bytes() for s in SLOTS)).hexdigest()
        stamp = ROOT / ".panel_slots.json"
        try:
            stored = json.loads(stamp.read_text())
        except (OSError, ValueError):
            stored = {}
        if not force and stored.get(self.address) == digest:
            return
        for state, (slot, _) in SLOTS.items():
            for attempt in range(3):
                try:
                    await self.client.send_image(str(BUILD / f"{state}.gif"), save_slot=slot)
                    break
                except RuntimeError as e:
                    log.warning("upload %s try %d: %r", state, attempt + 1, e)
                    await asyncio.sleep(1)
            else:
                raise RuntimeError(f"upload {state} failed 3 times")
        stored[self.address] = digest
        stamp.write_text(json.dumps(stored))
        log.info("uploaded %d animations", len(SLOTS))

    async def show(self, state: str):
        slot, bright = SLOTS[state]
        async with self.lock:
            for attempt in (1, 2):
                try:
                    await self.ensure()
                    await self.client.set_brightness(bright)
                    await self.client.show_slot(slot)
                    return True
                except Exception as e:
                    log.warning("show %s failed (try %d): %r", state, attempt, e)
                    if self.client:  # drop the link; the next try reconnects and re-uploads
                        try:
                            await self.client.disconnect()
                        except Exception:
                            pass
                        self.client = None
            return False

    async def dim(self, level: int):
        async with self.lock:
            try:
                if self.connected():
                    await self.client.set_brightness(level)
            except Exception as e:
                log.warning("dim failed: %r", e)


class Daemon(asyncio.DatagramProtocol):
    def __init__(self, panel: Panel, stop: asyncio.Event):
        self.panel, self.stop = panel, stop
        self.pending = None
        self.last_event = time.time()
        self.state = "ready"

    def datagram_received(self, data, addr):
        msg = data.decode(errors="ignore").strip().lower()
        if msg == "quit":
            log.info("quit requested")
            self.stop.set()
            return
        if msg not in SLOTS:
            return
        log.info("event %s", msg)
        if self.pending:
            self.pending.cancel()
        self.pending = asyncio.ensure_future(self.handle(msg))

    async def handle(self, state):
        self.last_event = time.time()
        self.state = state
        await asyncio.shield(self.panel.show(state))  # a newer event must not cut an upload in half
        if state == "done":
            await asyncio.sleep(SPIN_SECONDS)
            self.state = "ready"
            await self.panel.show("ready")

    async def watchdog(self):
        """Reconnect quietly if the panel was unplugged; dim a long-idle 'ready'."""
        dimmed = False
        while not self.stop.is_set():
            await asyncio.sleep(30)
            if not self.panel.connected():
                ok = await self.panel.show(self.state)
                if ok:
                    log.info("reconnected")
                    dimmed = False
            if self.state == "ready" and time.time() - self.last_event > DIM_AFTER and not dimmed:
                await self.panel.dim(10)
                dimmed = True
            elif time.time() - self.last_event < DIM_AFTER:
                dimmed = False


async def run():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    address = panel_address()
    if not address:
        sys.exit("Set [panel] address in config.toml (python morning.py scan)")
    panel = Panel(address)
    try:
        transport, proto = await loop.create_datagram_endpoint(
            lambda: Daemon(panel, stop), local_addr=("127.0.0.1", PORT))
    except OSError:
        log.info("already running, exiting")  # port taken = another instance holds the panel
        return
    log.info("listening on udp %d for panel %s", PORT, address)
    await panel.show("ready")
    dog = asyncio.ensure_future(proto.watchdog())
    await stop.wait()
    dog.cancel()
    transport.close()
    if panel.client:
        try:
            await panel.client.disconnect()
        except Exception:
            pass
    log.info("stopped")


def send(msg: str):
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(msg.encode(), ("127.0.0.1", PORT))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        send("quit")
    else:
        setup_logging()
        asyncio.run(run())
