import re

input_file = "sample_with_backticks.py"
output_file = "sample_cleaned.py"

with open(input_file, "r", encoding="utf-8") as f:
    content = f.read()

# Remove triple backticks (with or without json)
cleaned = re.sub(r"```(?:json)?", "", content, flags=re.IGNORECASE)

# Also remove any stray closing ```
cleaned = re.sub(r"```", "", cleaned)

with open(output_file, "w", encoding="utf-8") as f:
    f.write(cleaned)

print(f"Cleaned file written to {output_file}")