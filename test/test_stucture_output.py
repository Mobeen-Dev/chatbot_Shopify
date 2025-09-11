import json 
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict
from typing import Optional, List, Literal, Dict, Any, cast, Mapping, Tuple
from openai.types.chat import ChatCompletionMessageToolCall, ChatCompletionMessageParam, ChatCompletionToolMessageParam,  ChatCompletionMessage, ChatCompletionSystemMessageParam
import re


data1 = """
```json
{
"link": "https://digilog.pk/products/esp-01-esp8266-wifi-module-in-pakistan",
"imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/ESP01_ESP_01_ESP8266_WiFi_Module_lahore_islamabad_karachi_multan_rawalpindi_1f5c781b-3dd8-4918-8043-18e105f0fd20.webp?v=1735049240&width=1400",
"title": "Esp01 Esp 01 Esp8266 Wifi Module",
"price": "290 PKR",
"variants_options" : ["Default Title"],
"description": "ESP8266 WiFi Module provides integrated TCP/IP stack for easy WiFi access with any microcontroller. It features low power consumption, 1MB flash memory, supports SPI, UART, and integrated power management for efficient performance."
}
```
```product
{
"link": "https://digilog.pk/products/arduino-mkr1000-wifi-board-module-in-pakistan",
"imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/Arduino_MKR1000_WiFi_Board_Module_In_Lahore_Karachi_Islamabad_Peshawar_Quetta_Mardan_Multan_Sibbi_Hyderabad_Faisalabad_Rawalpindi_Pakistan__1.webp?v=1735057239&width=1400",
"title": "Arduino Mkr1000 Wifi Board Module",
"price": "5,500 PKR",
"variants_options" : ["Default Title"],
"description": "Arduino MKR1000 WiFi Board combines functional power with ease of use for IoT projects. It includes low power ARM MCU, encryption chip, LiPo battery charger, and supports WiFi b/g/n, ideal for secure and versatile networking."
}
```
```product
{
"link": "https://digilog.pk/products/ai-thinker-nodemcu-ai-wb2-13-wifi-bluetooth-5-0-module",
"imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/Ai-ThinkerNodeMCU-Ai-WB2-13WiFiBluetooth5.0Module.webp?v=1735048366&width=1400",
"title": "Ai-thinker Nodemcu-ai-wb2-13 Wifi Bluetooth 5.0 Module",
"price": "900 PKR",
"variants_options" : ["Default Title"],
"description": "Ai-Thinker WB2-13 Kit supports IEEE 802.11 b/g/n WiFi and Bluetooth BLE 5.0 with robust security protocols. Features include 32-bit RISC CPU, multiple interfaces, low power consumption, suitable for IoT, smart home, and wearable applications."
}
```
```product
{
"link": "https://digilog.pk/products/wt32-eth01-embedded-serial-port-networking-ethernet-ble-wifi-combo-gateway-mcu-esp32-wireless-module-board-wt32-eth01",
"imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/WT32ETH01.webp?v=1735046836&width=1400",
"title": "Wt32-eth01 Embedded Serial Port Networking Ethernet Ble Wifi Combo Gateway Mcu Esp32 Wireless Module Board Wt32 Eth01",
"price": "3,800 PKR",
"variants_options" : ["Default Title"],
"description": "WT32-ETH01 is a versatile IoT gateway module with ESP32 MCU offering WiFi, Bluetooth, Ethernet, and serial port connectivity. Perfect for industrial automation, smart home projects, and remote monitoring applications."
}
```
"""

data22 = """
```json
{
  "id": "gid://shopify/Cart/hWN2a8uYLxk8Lcn16fGm1Wom?key=ffccb89ca229089966ba0ae5bef1b0c0",
  "checkoutUrl": "https://store-mobeen-pk.myshopify.com/cart/c/hWN2a8uYLxk8Lcn16fGm1Wom?key=ffccb89ca229089966ba0ae5bef1b0c0",
  "subtotalAmount": "0.0 PKR",
  "lineItems": [
    {
      "id": "gid://shopify/CartLine/a72ac2a5-8486-4282-90b2-a576d0d08973?cart=hWN2a8uYLxk8Lcn16fGm1Wom",
      "variant_id": "gid://shopify/ProductVariant/41220052746326",
      "quantity": 0
    }
  ]
}
```
"""

test_cart_text = """
Here is a Shopify cart object we received:

{
    "id": "gid://shopify/Cart/1234567890",
    "checkoutUrl": "https://checkout.shopify.com/1234567890",
    "subtotalAmount": "$129.99",
    "lineItems": [
        {
            "title": "Blue T-Shirt",
            "quantity": 2,
            "price": "$29.99"
        },
        {
            "title": "Black Jeans",
            "quantity": 1,
            "price": "$69.99"
        }
    ]
}

Thanks.
"""


data3 = """
```json
{
    "id": "gid://shopify/Cart/hWN2a9Jvj5IRGIK4fZCczGAW?key=94d2d93dbe9f6aa8daeafae85b7fd443",
    "checkoutUrl": "https://store-mobeen-pk.myshopify.com/cart/c/hWN2a9Jvj5IRGIK4fZCczGAW?key=94d2d93dbe9f6aa8daeafae85b7fd443",
    "subtotalAmount": "0.0 PKR",
    "lineItems": [
        {
            "id": "gid://shopify/CartLine/9bd32f3d-9a27-4bad-8ce4-f14b5631cb6c?cart=hWN2a9Jvj5IRGIK4fZCczGAW",
            "variant_id": "gid://shopify/ProductVariant/41219772448854",
            "quantity": 0
        }
    ]
}
```
"""

data4 = """
```json
{
    "OrderID": "#12341",
    "FinancialStatus": "Paid",
    "FulfillmentStatus": "Shipped",
    "CustomerName": "Syed Raza Gufran",
    "CustomerPhone": "0321******51",
    "CustomerEmail": "dev**********gmail.com",
    "Items": " - Surfing Product, Qty: 12 ",
    "ShippingAddress": "st 12 house no 234 main colony newyork sector d",
    "Total": "$249.99"
}
```
"""

test_text = """
Hello team, please check this order:

{
    "OrderID": "#12341",
    "FinancialStatus": "Paid",
    "FulfillmentStatus": "Shipped",
    "CustomerName": "Syed Raza Gufran",
    "CustomerPhone": "0321******51",
    "CustomerEmail": "dev**********gmail.com",
    "Items": " - Surfing Product, Qty: 12, UnitPrice : 234 PKR \n  - Safety Product, Qty: 4, UnitPrice : 120 PKR \n  - Saketing Product, Qty: 6, UnitPrice : 234 PKR \n",
    "ShippingAddress": "st 12 house no 234 main colony newyork sector d",
    "Total": "$249.99"
}

Thanks.
"""

gpt5_output = 'Here are great WiFi-ready microcontroller boards for IoT projects. Pick based on your performance needs, budget, and form factor preference.\n\n```product\n{\n"link": "https://digilog.pk/products/espressif-esp32-wroom-32d-development-board",\n"imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/Espressif_ESP32_WROOM_32D_Development_Board.webp?v=1735056350",\n"title": "Espressif Esp32 Wroom 32d Development Board Esp32d Esp 32d",\n"price": "1,199 PKR",\n"variants_options" : ["Default Title"],\n"description": "Dual‑core 240 MHz ESP32 with 802.11 b/g/n Wi‑Fi and Bluetooth (Classic + BLE) • 4MB flash, CP2102 USB‑UART, breadboard‑friendly headers • Rich peripherals: ADC, DAC, UART, SPI, I2C, PWM, touch, hall sensor • AWS FreeRTOS/ESP‑IDF/Arduino IDE support • Ideal for robust IoT, home automation, sensors, and gateways at a great value"\n}\n```\n\n```product\n{\n"link": "https://digilog.pk/products/raspberry-pi-pico-w",\n"imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/Raspberry_Pi_Pico_W_1_4807f6c2-75a5-4121-8ae9-4a90a7998461.webp?v=1735105109",\n"title": "Raspberry Pi Pico w",\n"price": "2,700 PKR",\n"variants_options" : ["Default Title"],\n"description": "RP2040 dual‑core 133 MHz with 2.4 GHz 802.11n Wi‑Fi (CYW43439) • 26 GPIO, 2MB flash, PIO, ADC, PWM • Compact, low‑power board ideal for sensors and automation • Program with MicroPython or C/C++ • Great for learning, quick prototyping, and Wi‑Fi‑enabled embedded tasks"\n}\n```\n\n```product\n{\n"link": "https://digilog.pk/products/nodemcu-v2-lua-esp8266-development-board-cp2102-in-pakistan",\n"imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/CP2102_NodeMcu_v2_ESP8266_Lua_ESP8266_WIFI_Development_Board_IoT_Development_Board_3b75fb14-0c10-433b-a550-1224bf7cb475.webp?v=1735049397",\n"title": "NodeMCU V2 Lua Wifi Iot Development Board Esp 12E Esp8266 In Pakistan",\n"price": "680 PKR",\n"variants_options" : ["Default Title"],\n"description": "Budget‑friendly ESP8266 Wi‑Fi board for simple IoT • 11 b/g/n Wi‑Fi, TCP/IP stack • Easy USB programming via CP2102; Arduino IDE and Lua supported • Breadboard‑friendly, onboard 3.3V regulator • Best for basic Wi‑Fi sensors, relays, and dashboards at ultra‑low cost"\n}\n```\n\n```product\n{\n"link": "https://digilog.pk/products/esp32-cam-wifi-bluetooth-camera-module-development-board-esp32-with-camera-module-ov2640-for-arduino",\n"imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/ESP32-CAM_WiFi___Bluetooth_Camera_Module_Development_Board_ESP32_With_Camera_Module_OV2640_islamabad_karachi_e0458bad-9c46-4dbf-850e-3e8bb74f848d.webp?v=1735050012",\n"title": "Esp32-cam Wifi + Bluetooth Camera Module Development Board Esp32 With Camera Module Ov2640 For Arduino",\n"price": "1,499 PKR",\n"variants_options" : ["Default Title"],\n"description": "ESP32 with Wi‑Fi + BLE and OV2640 camera for vision‑enabled IoT • Captures JPEG, supports TF card storage • Compact module for wireless streaming, surveillance, smart doorbells, and image‑based automation • Arduino/ESP‑IDF compatible for fast prototyping"\n}\n```'

def extract_json_objects(text: str) -> Tuple[List[dict[str, Any]], str]:
    _CURRENCY_SYMBOLS = "€£$₹"
    _CURRENCY_CODE = r"[A-Z]{2,5}"

    _price_leading = re.compile(
        rf"^(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])\s*\d+(?:,\d{{3}})*(?:\.\d+)?$"
    )
    _price_trailing = re.compile(
        rf"^\d+(?:,\d{{3}})*(?:\.\d+)?\s*(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])$"
    )
    _price_range = re.compile(
    rf"^\d+(?:,\d{{3}})*(?:\.\d+)?\s*-\s*\d+(?:,\d{{3}})*(?:\.\d+)?\s*(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])$"
)

    def _valid_price(s: str) -> bool:
        s = s.strip()
        return bool(_price_leading.match(s) or _price_trailing.match(s) or _price_range.match(s))

    def _valid_product(obj: Any) -> bool:
        if not isinstance(obj, dict):
            return False
        required = {"link", "imageurl", "title", "price", "description"}
        if not required.issubset(obj.keys()):
            return False
        if not all(isinstance(obj[k], str) and "\n" not in obj[k] for k in required):
            return False
        if not (obj["link"].startswith("https://") and obj["imageurl"].startswith("https://")):
            return False
        if obj["price"].strip() and not _valid_price(obj["price"]):
            return False
        return True

    def _valid_cart(obj: Any) -> bool:
        if not isinstance(obj, dict):
            return False
        required = {"id", "checkoutUrl", "subtotalAmount", "lineItems"}
        if not required.issubset(obj.keys()):
            return False
        if not all(
            isinstance(obj[k], str) and "\n" not in obj[k]
            for k in ["id", "checkoutUrl", "subtotalAmount"]
        ):
            return False
        if not obj["id"].startswith("gid://shopify/Cart/"):
            return False
        if not obj["checkoutUrl"].startswith("https://"):
            return False
        if obj["subtotalAmount"].strip() and not _valid_price(obj["subtotalAmount"]):
            return False
        if not isinstance(obj["lineItems"], list):
            return False
        if not all(isinstance(item, dict) for item in obj["lineItems"]):
            return False
        return True

    def _valid_order(obj: Any) -> bool:
        """Lenient check for order JSON."""
        if not isinstance(obj, dict):
            return False
        orderish_keys = {
            "OrderID", "FinancialStatus", "FulfillmentStatus",
            "CustomerName", "CustomerPhone", "CustomerEmail",
            "Items", "ShippingAddress", "Total"
        }
        return any(k in obj for k in orderish_keys)

    # ---------- Text utilities ----------
    def _remove_spans(s: str, spans: List[Tuple[int, int]]) -> str:
        if not spans:
            return s
        spans = sorted(spans)
        out, prev = [], 0
        for a, b in spans:
            out.append(s[prev:a])
            prev = b
        out.append(s[prev:])
        return "".join(out)

    def _find_json_objects(text: str) -> List[Tuple[int, int, str]]:
        results: List[Tuple[int, int, str]] = []
        stack = 0
        in_str = False
        esc = False
        start = -1
        for i, ch in enumerate(text):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    if stack == 0:
                        start = i
                    stack += 1
                elif ch == "}":
                    if stack > 0:
                        stack -= 1
                        if stack == 0 and start != -1:
                            end = i + 1
                            results.append((start, end, text[start:end]))
                            start = -1
        return results

    results: List[dict[str, Any]] = []
    remove_spans: List[Tuple[int, int]] = []

    # 1) Handle fenced blocks
    fenced = re.compile(r"```(product|cart|order)\s*(.*?)```", re.DOTALL)
    for m in fenced.finditer(text):
        block_type = m.group(1).lower()
        block_content = m.group(2).strip()

        try:
            obj = json.loads(block_content)
        except json.JSONDecodeError:
            continue

        if block_type == "product" and _valid_product(obj):
            obj["type"] = "Product"
            results.append(obj)
            remove_spans.append((m.start(), m.end()))
        elif block_type == "cart" and _valid_cart(obj):
            obj["type"] = "Cart"
            results.append(obj)
            remove_spans.append((m.start(), m.end()))
        elif block_type == "order" and _valid_order(obj):
            obj["type"] = "Order"
            results.append(obj)
            remove_spans.append((m.start(), m.end()))

    intermediate = _remove_spans(text, remove_spans)

    # 2) Unfenced JSON objects
    spans2: List[Tuple[int, int]] = []
    for s, e, raw in _find_json_objects(intermediate):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if _valid_product(obj):
            obj["type"] = "Product"
            results.append(obj)
            spans2.append((s, e))
        elif _valid_cart(obj):
            obj["type"] = "Cart"
            results.append(obj)
            spans2.append((s, e))
        elif _valid_order(obj):
            obj["type"] = "Order"
            results.append(obj)
            spans2.append((s, e))

    cleaned_text = _remove_spans(intermediate, spans2).strip()
    cleaned_text = re.sub(r"\[\s*\]", "", cleaned_text)
    cleaned_text = re.sub(r"\[\s*(?:,\s*)*\]", "", cleaned_text)
    cleaned_text = re.sub(r"```(?:json|product|cart|order)?\s*```", "", cleaned_text, flags=re.MULTILINE)

    return results, cleaned_text.strip()



wow = """
```cart
{
    "id": "gid://shopify/Cart/hWN2grAtOUpAPbnPCjS4ctcZ?key=93c8dda56f995f99a10ac018607962f5",
    "checkoutUrl": "https://store-mobeen-pk.myshopify.com/cart/c/hWN2grAtOUpAPbnPCjS4ctcZ?key=93c8dda56f995f99a10ac018607962f5",
    "subtotalAmount": "680.00 PKR",
    "lineItems": "Pass the dictionary exactly as received — no modifications, no renaming, no restructuring."
}
```
"""

wow = """```product\n{\n\"link\": \"https://digilog.pk/products/smart-watch-t900-ultra-2-09-inch-big-display-bluetooth-calling-series-8-with-all-sports-features-health-tracker-smart-watch-ultra-infinite-display-with-wireless-charger-men-women-smart-watch\",\n\"imageurl\": \"https://cdn.shopify.com/s/files/1/0559/7832/8150/files/T900-Ultra-Series-8-Smartwatch.webp?v=1735045538\",\n\"title\": \"Smart Watch T900 Ultra 2.09 Inch Big Display Bluetooth Calling Series 8 With All Sports Features & Health Tracker - Smart Watch Ultra Infinite Display\",\n\"price\": \"1,650 - 1,850 PKR\",\n\"variants_options\" : [\"Black\",\"Orange\"],\n\"description\": \"2.09-inch bright touchscreen; Bluetooth calling and notifications; 24/7 heart rate, SpO2, blood pressure and sleep tracking; Multiple sports modes and customizable dials; Durable titanium-style build with large controls; Compatible with Android & iOS; Affordable value for daily health and activity tracking.\"\n}\n```"""
wwow = """Here are the recommended Digilog parts to build an ESP32-S3 AI voice assistant. I can add any of these to your cart (use your session_id) if you want.\n\n```product\n{\n"link":"https://digilog.pk/products/esp32-s3-wroom-1-development-board-in-pakistan-esp-32-s3",\n"imageurl":"https://cdn.shopify.com/s/files/1/0559/7832/8150/files/ESP32S3Wroom1DevelopmentBoardInPakistanESP32S3.webp?v=1735040600",\n"title":"ESP32 S3 Wroom 1 Development Board In Pakistan ESP 32 S3 with cable",\n"price":"1350 PKR",\n"variants_options":["Default Title"],\n"description":"ESP32-S3 development board with Wi‑Fi and Bluetooth LE; up to 240 MHz dual-core LX7 MCU; native USB OTG and debug; I2S/I2C/SPI/ADC interfaces for audio and peripherals; ideal for on-device ML and voice projects"\n}\n```\n\n```product\n{\n"link":"https://digilog.pk/products/inmp441-mems-high-precision-omnidirectional-microphone-i2s-snr-low-power-module",\n"imageurl":"https://cdn.shopify.com/s/files/1/0559/7832/8150/files/1n.webp?v=1735040564",\n"title":"INMP441 MEMS High Precision Omnidirectional Microphone I2S SNR Low Power Module",\n"price":"800 PKR",\n"variants_options":["Default Title"],\n"description":"Digital I2S MEMS microphone with 24-bit output; high SNR (~61 dBA) and flat 60 Hz–15 kHz response; low current draw and 1.8–3.3V operation; plug-and-play for ESP32 I2S input and wake-word/voice capture"\n}\n```\n\n```product\n{\n"link":"https://digilog.pk/products/max98357-i2s-pcm-digital-audio-amplifier-board-3w-class-d-dac-decoder",\n"imageurl":"https://cdn.shopify.com/s/files/1/0559/7832/8150/files/MAX983573.webp?v=1735040555",\n"title":"MAX98357 I2S PCM Digital Audio Amplifier Board - 3W Class D DAC Decoder",\n"price":"650 PKR",\n"variants_options":["Default Title"],\n"description":"Compact I2S Class‑D DAC amplifier with up to 3W output; accepts I2S from ESP32‑S3 for direct digital audio playback; efficient low-power design perfect for small speakers in voice assistants"\n}\n```\n\n```product\n{\n"link":"https://digilog.pk/products/8-ohm-3-watts-woofer-speaker-loudspeaker-for-arduino-in-pakistan",\n"imageurl":"https://cdn.shopify.com/s/files/1/0559/7832/8150/files/8_Ohm_3_Watts_Woofer_Loud_Speaker_Loudspeaker_For_Arduino_DIY_Projects_In_Lahore_Karachi_Islamabad_Peshawar_Quetta_Mardan_Multan_Hyderabad_Faisalabad_Khushab_Sahiwal_Pakistan___1.webp?v=1735066020",\n"title":"8 Ohm 3 Watts Woofer Loud Speaker Loudspeaker For Arduino Diy Projects",\n"price":"100 PKR",\n"variants_options":["Default Title"],\n"description":"2\\" full-range 8Ω 3W speaker for compact projects; good match for MAX98357 amplifier; small form factor suitable for tabletop voice assistant enclosures"\n}\n```\n\n```product\n{\n"link":"https://digilog.pk/products/arduino-0-96-inch-iic-oled-display-128x64-i2c-ssd1306-lcd-screen-in-pakistan",\n"imageurl":"https://cdn.shopify.com/s/files/1/0559/7832/8150/files/Arduino_0.96_inch_IIC_OLED_Display_128X64_I2C_SSD1306_LCD_Screen_In_Lahore_Karachi_Islamabad_Peshawar_Quetta_Mardan_Multan_Pakistan__3_2a88be66-1d7e-4717-a87e-a615a782bd19.webp?v=1735049454",\n"title":"Arduino 0.96 Inch OLED Display Module 128x64 I2C SSD 1306 LCD Screen",\n"price":"490 PKR",\n"variants_options":["Default Title"],\n"description":"0.96\\" 128x64 SSD1306 I2C OLED display; uses I2C address 0x3C; ultra-low power and wide viewing angle; ideal for showing status, prompts, or simple UI on your assistant"\n}\n```\n\n```product\n{\n"link":"https://digilog.pk/products/tp4056-lithium-battery-charging-board-1a-type-c-in-pakistan",\n"imageurl":"https://cdn.shopify.com/s/files/1/0559/7832/8150/files/tp4056-lithium-battery-charging-board-1a-type-c_in_Pakistan.webp?v=1735057246",\n"title":"Type c Tp4056 Lithium Battery Charging Board 1a",\n"price":"45 PKR",\n"variants_options":["Default Title"],\n"description":"Type‑C TP4056 Li‑ion charging board with 1A charge current and battery protection features; compact solution to charge a single-cell LiPo used to power your portable assistant"\n}\n```\n\nIf you want, I can:\n- add a selected set of these items to your cart now using your session_id, or\n- include a short wiring checklist and minimal Arduino/ESP‑IDF code for wake-word + TTS playback. Which would you like next?

"""

###############################3
stucture_output, reply = extract_json_objects(str(wwow))

print("stucture_output", stucture_output)
print("\n---- cleaned ----\n")
print("reply", reply)









