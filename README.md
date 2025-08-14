📡 Async Gammu SMS Gateway

<img width="322" height="270" alt="image" src="https://github.com/user-attachments/assets/9695520e-eb64-40a2-9041-2b223e3561b3" />

This is an asynchronous SMS gateway built with Python, aiohttp, and gammu, designed to send and receive SMS messages via HTTP endpoints. It supports integration with Home Assistant using supervisor events. 

Disclaimer: 
I am just uploading so others can use it, since the Integration has been deprecated. There probably wont be updates from me, fork if you need something changed or updated.

📦 Features
```
  📤 Send SMS via HTTP POST /send
  
  📥 Receive SMS and expose them via /inbox
  
  📶 Check GSM signal strength via /signal
  
  🔄 Polls GSM device asynchronously for new messages
  
  🏠 Optional Home Assistant integration via Supervisor events
```
🧰 Requirements

- Home Assistant OS

- A compatible GSM modem or device. I used the SIM800C

🛠️ Installation

- Copy grimsms folder to /addons directory
- Copy grim_sms to /config/custom_components
- Go to Devices and services and search for "Grim SMS Gateway" and install.

The custom component will create the Entities
- sensor.grim_sms_gateway_health # health of the gateway
- sensor.grim_sms_last_message # Last message received, used for auotmations or abything else.
- sensor.grim_sms_signal_strength # Check signal

⚙️ Addon Environment Variables
- Variable	Description	Default

- PORT	Port the API will listen on	8002
- GAMMU_DEVICE	Path to GSM modem device	/dev/serial/by-id/xxxxxx
- GAMMU_BAUDSPEED	Baud rate for the modem (Gammu connection string)	at115200

API Endpoints

POST /send

Send an SMS.
An example for Home assistant is to create a rest command in your config file like:
```
rest_command:
  smssendrest:
      url: "http://your-ha-ip-here:8002/send"
      method: post
      content_type: "application/json"
      timeout: 30
      payload: >
          {
              "number": "your-number-here",
              "message": "{{ message }}"
          }
```

Request:
```
{
  "number": "+1234567890",
  "message": "Hello from Gammu!"
}
```
Response:
```
{ "status": "sent" }
```

And use it in an automation and send the text in the message variable:
```
alias: CheckDown
description: ""
triggers:
  - entity_id:
      - binary_sensor.internet
    from: "on"
    to: "off"
    trigger: state
conditions: []
actions:
  - action: rest_command.smssendrest
    metadata: {}
    data:
      message: HA Down!
mode: single

```
GET /inbox

Returns a list of received SMS messages.

Response:
```
[
  {
    "number": "+1234567890",
    "text": "Hi there!",
    "timestamp": "2025-08-14 13:37:00"
  }
]
```
Then you can use it to capture the text in the SMS in an automation and trigger a device:
```
alias: SMS - Turn Off Office Light
description: Turn off the office light when SMS message says "Office light off"
triggers:
  - entity_id: sensor.grim_sms_last_message
    trigger: state
conditions:
  - condition: template
    value_template: |
      {{ states('sensor.grim_sms_last_message') | lower == 'office light off' }}
actions:
  - action: light.turn_off
    data: {}
    target:
      device_id: deviceId
mode: single

```
GET /signal

Returns signal quality of the modem.

Response:
```
{
  "signal_percent": 90,
  "signal_dbm": -65,
  "bit_error_rate": 0,
  "raw": { ... }
}
```
GET /health

Simple health check. Returns OK.

🏠 Home Assistant Integration

If HASSIO_TOKEN is set, received SMS messages will be automatically posted to Home Assistant via:
POST http://supervisor/core/api/events/sms_received
Each message will include:
```
{
  "number": "+1234567890",
  "text": "Message body",
  "timestamp": "..."
}
```
🧪 Development & Debugging

Logs are printed to stdout with INFO level by default.

Polling interval for new SMS: 10 seconds

Messages are deleted from modem after reading.
