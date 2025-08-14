import asyncio
import os
import logging
import aiohttp
import subprocess
import serial
from aiohttp import web
import gammu

logging.basicConfig(level=logging.INFO)
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
_LOGGER = logging.getLogger("sms_gateway.api")

SUPERVISOR_API = "http://supervisor/core/api/events/sms_received"
SUPERVISOR_TOKEN = os.getenv("HASSIO_TOKEN")

def write_gammurc():
    gammu_device = os.getenv("GAMMU_DEVICE", "/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0")
    gammu_connection = os.getenv("GAMMU_BAUDSPEED", "at115200")
    
    _LOGGER.info(f"Gammu device: {gammu_device}, connection: {gammu_connection}")
    if not gammu_device or not gammu_connection:
        _LOGGER.error("GAMMU_DEVICE or GAMMU_BAUDSPEED env vars are missing or empty!")
        raise RuntimeError("Missing gammu device or connection environment variables")
    
    gammu_config = f"""
[gammu]
port = {gammu_device}
connection = {gammu_connection}
"""
    with open("/etc/gammurc", "w") as f:
        f.write(gammu_config)

class GammuAsyncWrapper:
    def __init__(self, config_path="/etc/gammurc"):
        self.state_machine = gammu.StateMachine()
        self.state_machine.ReadConfig(Filename=config_path)
        self.state_machine.Init()
        self.inbox = []

    async def send_sms(self, text, number):
        loop = asyncio.get_event_loop()
        smsc = await loop.run_in_executor(None, self.state_machine.GetSMSC)
        message = {
            'Text': text,
            'SMSC': smsc,
            'Number': number,
        }
        _LOGGER.debug(f"Sending SMS with message payload: {message}")
        await loop.run_in_executor(None, self.state_machine.SendSMS, message)
        _LOGGER.info("SMS sent successfully.")

    async def poll_sms(self):
        while True:
            loop = asyncio.get_event_loop()
            try:
                _LOGGER.debug("Polling for incoming SMS...")
                parts = await loop.run_in_executor(None, self.state_machine.GetNextSMS, 0, True)
                for message in parts:
                    _LOGGER.info(f"Received SMS from {message['Number']}: {message['Text']}")
                    sms_data = {
                        "number": message["Number"],
                        "text": message["Text"],
                        "timestamp": str(message.get("DateTime", "")),
                    }
                    self.inbox.append(sms_data)
                    await fire_ha_event(sms_data)

                    # Delete SMS after reading
                    if "Folder" in message and "Location" in message:
                        await loop.run_in_executor(None, self.state_machine.DeleteSMS, message["Folder"], message["Location"])
            except gammu.ERR_EMPTY:
                # No new messages
                pass
            except Exception as e:
                _LOGGER.error(f"Error while polling SMS: {e}")

            await asyncio.sleep(10)

async def fire_ha_event(event_data):
    if not SUPERVISOR_TOKEN:
        _LOGGER.warning("SUPERVISOR_TOKEN not set. Cannot fire event to Home Assistant.")
        return

    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(SUPERVISOR_API, headers=headers, json=event_data) as resp:
                if resp.status != 200:
                    _LOGGER.error(f"Failed to fire event to Home Assistant: HTTP {resp.status}")
                else:
                    _LOGGER.debug("Event fired successfully to Home Assistant.")
    except Exception as e:
        _LOGGER.error(f"Exception firing event to Home Assistant: {e}")

async def send_sms(request):
    data = await request.json()
    number = data.get("number")
    text = data.get("message")

    if not number or not text:
        return web.json_response({"error": "Missing number or message"}, status=400)

    try:
        handler = request.app["handler"]
        await handler.send_sms(text=text, number=number)
        return web.json_response({"status": "sent"})
    except Exception as e:
        _LOGGER.error("Failed to send SMS: %s", e)
        return web.json_response({"error": str(e)}, status=500)

async def get_inbox(request):
    handler = request.app["handler"]
    return web.json_response(handler.inbox)

async def get_signal(request):
    handler = request.app["handler"]
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, handler.state_machine.GetSignalQuality)
        _LOGGER.debug(f"GetSignalQuality raw result: {result}")

        signal = result.get("SignalPercent")  # Or use "SignalStrength" if you prefer dBm
        return web.json_response({
            "signal_percent": signal,
            "signal_dbm": result.get("SignalStrength"),
            "bit_error_rate": result.get("BitErrorRate"),
            "raw": result
        })
    except Exception as e:
        _LOGGER.error(f"Failed to get signal quality: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def init_app():
    write_gammurc()
    app = web.Application()

    handler = GammuAsyncWrapper(config_path="/etc/gammurc")
    app["handler"] = handler

    app.router.add_post("/send", send_sms)
    app.router.add_get("/health", lambda _: web.Response(text="OK"))
    app.router.add_get("/inbox", get_inbox)
    app.router.add_get("/signal", get_signal)
    # Removed /balance route

    asyncio.create_task(handler.poll_sms())

    return app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8002))
    web.run_app(init_app(), host="0.0.0.0", port=port)
