import json 
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict
from typing import Optional, List, Literal, Dict, Any, cast, Mapping, Tuple
from openai.types.chat import ChatCompletionMessageToolCall, ChatCompletionMessageParam, ChatCompletionToolMessageParam,  ChatCompletionMessage, ChatCompletionSystemMessageParam
import re


data = """
```product
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

data2 = """
```cart
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

data3 = """
```cart
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




def extract_json_objects2(text: str) -> Tuple[List[dict[str, Any]], str]:
    _CURRENCY_SYMBOLS = "€£$₹"
    _CURRENCY_CODE = r"[A-Z]{2,5}"

    _price_leading = re.compile(
        rf"^(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])\s*\d+(?:,\d{{3}})*(?:\.\d+)?$"
    )
    _price_trailing = re.compile(
        rf"^\d+(?:,\d{{3}})*(?:\.\d+)?\s*(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])$"
    )

    def _valid_price(s: str) -> bool:
        s = s.strip()
        return bool(_price_leading.match(s) or _price_trailing.match(s))

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
      if not all(isinstance(obj[k], str) and "\n" not in obj[k] for k in required if k in obj):
          return False
      if not obj["id"].startswith("gid://shopify/Cart/"):
          return False
      if not obj["checkoutUrl"].startswith("https://"):
          return False
      if obj["subtotalAmount"].strip() and not _valid_price(obj["subtotalAmount"]):
          return False
      return True

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

    # 1) Handle fenced blocks: ```product or ```cart
    fenced = re.compile(r"```(product|cart)(.*?)```", re.DOTALL)
    for m in fenced.finditer(text):
        block_type = m.group(1).lower()
        block_content = m.group(2)

        # Find ALL {...} inside the block
        for obj_match in re.finditer(r"\{.*?\}", block_content, re.DOTALL):
            raw = obj_match.group(0)
            try:
                obj = json.loads(raw)
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

    cleaned_text = _remove_spans(intermediate, spans2).strip()
    cleaned_text = re.sub(r"\[\s*\]", "", cleaned_text)
    cleaned_text = re.sub(r"\[\s*(?:,\s*)*\]", "", cleaned_text)
    cleaned_text = re.sub(r"```(?:json|product|cart)?\s*```", "", cleaned_text, flags=re.MULTILINE)

    return results, cleaned_text.strip()


def extract_json_objects(text: str) -> Tuple[List[dict[str, Any]], str]:
      _CURRENCY_SYMBOLS = "€£$₹"
      _CURRENCY_CODE = r"[A-Z]{2,5}"

      _price_leading = re.compile(
          rf"^(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])\s*\d+(?:,\d{{3}})*(?:\.\d+)?$"
      )
      _price_trailing = re.compile(
          rf"^\d+(?:,\d{{3}})*(?:\.\d+)?\s*(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])$"
      )

      def _valid_price(s: str) -> bool:
          s = s.strip()
          return bool(_price_leading.match(s) or _price_trailing.match(s))

      def _valid_product(obj: Any) -> bool:
          if not isinstance(obj, dict):
              return False
          required = {"link", "imageurl", "title", "price", "description"}
          if set(obj.keys()) != required:
              return False
          if not all(isinstance(v, str) and "\n" not in v for v in obj.values()):
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
          if set(obj.keys()) != required:
              return False
          if not all(isinstance(v, str) and "\n" not in v for v in obj.values()):
              return False
          if not obj["id"].startswith("gid://shopify/Cart/"):
              return False
          if not obj["checkoutUrl"].startswith("https://"):
              return False
          if obj["subtotalAmount"].strip() and not _valid_price(obj["subtotalAmount"]):
              return False
          return True

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

      # 1) Handle fenced blocks: ```product or ```cart
      fenced = re.compile(r"```(product|cart)\s*(\{.*?\})\s*```", re.DOTALL)
      for m in fenced.finditer(text):
          block_type = m.group(1).lower()
          raw = m.group(2)
          try:
              obj = json.loads(raw)
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

      cleaned_text = _remove_spans(intermediate, spans2).strip()
      cleaned_text = re.sub(r"\[\s*\]", "", cleaned_text)
      cleaned_text = re.sub(r"\[\s*(?:,\s*)*\]", "", cleaned_text)
      cleaned_text = re.sub(r"```(?:json|product|cart)?\s*```", "", cleaned_text, flags=re.MULTILINE)

      return results, cleaned_text.strip()




def extract_json_objects3(text: str) -> Tuple[List[dict[str, Any]], str]:
    _CURRENCY_SYMBOLS = "€£$₹"
    _CURRENCY_CODE = r"[A-Z]{2,5}"

    _price_leading = re.compile(
        rf"^(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])\s*\d+(?:,\d{{3}})*(?:\.\d+)?$"
    )
    _price_trailing = re.compile(
        rf"^\d+(?:,\d{{3}})*(?:\.\d+)?\s*(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])$"
    )

    def _valid_price(s: str) -> bool:
        s = s.strip()
        return bool(_price_leading.match(s) or _price_trailing.match(s))

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
        # id, checkoutUrl, subtotalAmount must be strings
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
        # lineItems must be a list of dicts
        if not isinstance(obj["lineItems"], list):
            return False
        if not all(isinstance(item, dict) for item in obj["lineItems"]):
            return False
        return True

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

    # 1) Handle fenced blocks: ```product or ```cart
    fenced = re.compile(r"```(product|cart)\s*(.*?)```", re.DOTALL)
    for m in fenced.finditer(text):
        block_type = m.group(1).lower()
        block_content = m.group(2).strip()

        # Try parsing block_content directly as JSON
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

    cleaned_text = _remove_spans(intermediate, spans2).strip()
    cleaned_text = re.sub(r"\[\s*\]", "", cleaned_text)
    cleaned_text = re.sub(r"\[\s*(?:,\s*)*\]", "", cleaned_text)
    cleaned_text = re.sub(r"```(?:json|product|cart)?\s*```", "", cleaned_text, flags=re.MULTILINE)

    return results, cleaned_text.strip()







###############################3
stucture_output, reply = extract_json_objects3(str(data2))

print("stucture_output", stucture_output)
print("reply", reply)









