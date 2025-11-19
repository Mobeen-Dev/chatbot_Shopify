from rs_bpe.bpe import openai

# Load OpenAI-compatible tokenizer (same as GPT-4o / gpt-3.5-turbo)
encoder = openai.cl100k_base()

text = "product_title : 1 Meter 18650 Nickel Strip Belt Tape Li-ion Battery Connector Spcc Spot Welding Bms Parts 0.12mm 5mm | product_handle : 1m-18650-nickel-strip-liion-battery-connector-in-pakistan | price_range : 60.0 PKR - 60.0 PKR 1 meter Nickel Strip has good weldability, high draw tention , easy to operate and low resistivity.This product is essential for the manufacturing of nickel cardium and nickel- hydrogen batteries, as well as battery combinations, power tools, special lamps , and various other industries. It finds extensive application in battery production, connector assembly, electronic component connection, and stamping processes. With its reliable performance and compatibility, it serves as a crucial component in the production and assembly of various electrical devices. Features of 1 meter Nickel Strip: Good luster, ductility, weldability With anti-abrasion performance Good properties and electrical conductivity on the tin Specifications: Material : Nickel+steel Current Rating : 5A Size : 0.12x5mm Thickness : 0.12mm Overall Length : 1m Suitable For : Manufacture nickel-metal hydride batteries, lithium batteries, Combination battery, and power tools newsletter, special lamps, and other industries Packing Include: 1x 1 Meter 18650 Strip Belt Tape Li-ion Battery Connector Spcc Spot Welding Bms Parts 0.12mm 5mm Buy this product at Pakistan best online shopping store digilog.pk at cheap price. We deliver in Gujranwala ,Karachi, Lahore, Islamabad , Rawalpindi , Multan, Quetta , Faisalabad and all over the Pakistan."

# Encode text -> list of token IDs
token_ids = encoder.encode(text)

# Decode back to verify integrity
decoded = encoder.decode(token_ids)

print("Original:", text)
print("Tokens:", token_ids, "\n")

print("Total token count:", len(token_ids))
print()
print("Decoded text:", decoded)

# Simple correctness test
assert text == decoded, "Error: Text was not decoded properly!"
print("✔ Test passed: Encoding/Decoding successful!")
