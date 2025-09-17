import re
import json
from typing import Any, List, Tuple
from Shopify import Shopify
from config import settings
# ---------- Validation helpers ----------

_CURRENCY_SYMBOLS = "€£$₹"
_CURRENCY_CODE = r"[A-Z]{2,5}"

_price_leading = re.compile(
    rf"^(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])\s*\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?$"
)
_price_trailing = re.compile(
    rf"^\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?\s*(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])$"
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
    # All single-line strings
    if not all(isinstance(v, str) and "\n" not in v for v in obj.values()):
        return False
    # https links
    if not (
        obj["link"].startswith("https://") and obj["imageurl"].startswith("https://")
    ):
        return False
    # price format (accepts code/symbol before or after)
    if not _valid_price(obj["price"]):
        return False
    return True


# ---------- Text utilities ----------


def _remove_spans(s: str, spans: List[Tuple[int, int]]) -> str:
    """Remove [start, end) spans from s in one pass."""
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
    """
    Return list of (start, end, json_str) for JSON objects found via brace scanning.
    Ignores braces inside quoted strings and handles escapes.
    """
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


# ---------- Main extractor ----------


def extract_and_remove_product_json(text: str) -> Tuple[List[dict[str, Any]], str]:
    results: List[dict[str, Any]] = []
    remove_spans: List[Tuple[int, int]] = []

    # 1) First handle fenced ```json blocks
    fenced = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    for m in fenced.finditer(text):
        raw = m.group(1)
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if _valid_product(obj):
            results.append(obj)
            remove_spans.append((m.start(), m.end()))

    # Remove fenced now so indices for the next pass are clean
    intermediate = _remove_spans(text, remove_spans)

    # 2) Find unfenced JSON objects via brace scanning
    spans2: List[Tuple[int, int]] = []
    for s, e, raw in _find_json_objects(intermediate):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if _valid_product(obj):
            results.append(obj)
            spans2.append((s, e))

    cleaned_text = _remove_spans(intermediate, spans2).strip()

    if len(cleaned_text) < 100:
        cleaned_text += (
            "\nCheckout the products Below."
            if cleaned_text
            else "Checkout the products Below."
        )

    return results, cleaned_text


# # Example usage:
# text_output = 'ajhf;jkasdfjkd fjasdfbkasd fks dk sadk vjkbdasfls sdlasd vsdkjvaskdklasdfkas;fior;jnvisuawijf rvaiv;sufsuvasid visduvbasid vad vasd```json\n{\n  "link": "https://digilog.pk/products/4wd-smart-robot-car-chassis-kit-for-arduino-in-pakistan",\n  "imageurl": "https://cdn.shopify.com/s/files/1/0744/0764/1366/files/Robot_Card_d64176e3-318e-4299-9cd9-09984a2b9fb7.webp?v=1723513853",\n  "title": "Imported Original 4wd Smart Robot Car Chassis Kit For Arduino",\n  "price": "PKR 250,000",\n  "description": "4-Wheel Robot Chassis Kit, easy to assemble and use with a large space for mounting sensors and electronics. Compatible with Arduino/Raspberry Pi and motor drivers, perfect for DIY learning, academic research, and hobby projects."\n}\n```\n\n```json\n{\n  "link": "https://digilog.pk/products/local-4wd-smart-robot-car-chassis-kit-for-arduino",\n  "imageurl": "https://cdn.shopify.com/s/files/1/0744/0764/1366/files/Local_4WD_Smart_Robot_Car_Chassis_Kit_For_Arduino_1.webp?v=1723480122",\n  "title": "Local 4wd Smart Robot Car Chassis Kit For Arduino",\n  "price": "PKR 225,000",\n  "description": "Affordable and durable 4WD Smart Robot Car Chassis Kit with 4 DC motors with encoders, a solid acrylic chassis, and durable wheels. Suitable for building autonomous, obstacle-avoiding, and line-following robots compatible with Arduino and Raspberry Pi."\n}\n```'
# text_output3 ='{\n  "link": "https://digilog.pk/products/4wd-smart-robot-car-chassis-kit-for-arduino-in-pakistan",\n  "imageurl": "https://cdn.shopify.com/s/files/1/0744/0764/1366/files/Robot_Card_d64176e3-318e-4299-9cd9-09984a2b9fb7.webp?v=1723513853",\n  "title": "Imported Original 4wd Smart Robot Car Chassis Kit For Arduino",\n  "price": "250,000 PKR",\n  "description": "4-Wheel Robot Chassis Kit, an easy to assemble and use robot chassis platform. The Arduino chassis kit provides you with everything you need to give your robot a fast four-wheel-drive platform with plenty of room for expansion to add various sensors and controllers. Just add your electronics - Arduino/Raspberry Pi and Motor Driver and you can start programming your robot. This smart robot car offers a large space with predrilled holes for mounting sensors and electronics as per your requirement. This robot chassis lets you get your mechanical platform ready in minutes and quickstart your robot building process. Wheeled Robots are the most popular robot platforms and are easy to run, maintain and use. Simple to build and program, this kit is the simplest robot platform. This best 4WD car robot kit is highly recommended for beginners and novice users. The 4WD kit lets you go faster, carry more weight, and carry bigger load compared to the 2WD Kit. You can build line-following robots, obstacle avoiding robots, and other robots using this kit."\n}'
# clean_list, remaining_text  = extract_and_remove_product_json(text_output3)
# print("\n\n\n\n\n\n")
# print("text_output :", clean_list)
# print("text_remaining :", remaining_text)
# # print(clean_list)
store = Shopify(settings.store)
value = {
    "data": {
        "cart": {
            "note": "This order was created with the help of AI.",
            "cost": {
                "subtotalAmount": {"amount": "5450.0", "currencyCode": "PKR"},
                "subtotalAmountEstimated": True,
                "totalAmount": {"amount": "5450.0", "currencyCode": "PKR"},
            },
            "id": "gid://shopify/Cart/hWN2Hiq8ybacnqpIHoZgfFid?key=84eda6e4b4dc9ac81376863649d5504c",
            "checkoutUrl": "https://store-mobeen-pk.myshopify.com/cart/c/hWN2Hiq8ybacnqpIHoZgfFid?key=84eda6e4b4dc9ac81376863649d5504c",
            "createdAt": "2025-08-27T13:22:25Z",
            "updatedAt": "2025-08-27T13:22:25Z",
            "lines": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/CartLine/c71bf793-bef0-417c-8378-12dcea7725a3?cart=hWN2Hiq8ybacnqpIHoZgfFid",
                            "merchandise": {
                                "id": "gid://shopify/ProductVariant/42551544545366"
                            },
                        }
                    },
                    {
                        "node": {
                            "id": "gid://shopify/CartLine/77b8f31d-d80c-43cf-86f6-32b3ea28e478?cart=hWN2Hiq8ybacnqpIHoZgfFid",
                            "merchandise": {
                                "id": "gid://shopify/ProductVariant/42394067828822"
                            },
                        }
                    },
                ]
            },
            "buyerIdentity": {
                "preferences": {"delivery": {"deliveryMethod": ["PICK_UP"]}}
            },
            "attributes": [{"key": "Chat #", "value": "default"}],
        }
    }
}

print(store.format_cart(value))
