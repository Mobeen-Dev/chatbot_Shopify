import markdown
from bs4 import BeautifulSoup

def markdown_to_html(md_text: str) -> str:
    # Step 1: Convert Markdown to raw HTML
    html = markdown.markdown(
        md_text,
        extensions=[
            'extra',        # tables, footnotes, etc.
            'codehilite',   # syntax highlighting (needs pygments)
            'nl2br',        # convert newlines to <br>
            'sane_lists'    # better list formatting
        ]
    )

    # Step 2 (Optional): Sanitize HTML (basic cleanup)
    soup = BeautifulSoup(html, "html.parser")

    # Optional: Remove unsafe tags (e.g., scripts)
    for tag in soup.find_all(["script", "iframe", "style"]):
        tag.decompose()

    return str(soup)


md_conetent = """
Certainly! Here's a complete example of Markdown with various elements:\n\n```markdown\n# This is an H1 Heading\n\n## This is an H2 Heading\n\n### This is an H3 Heading\n\n**This text is bold**\n\n*This text is italic*\n\n***This text is bold and italic***\n\n> This is a blockquote.\n> \n> It can span multiple lines.\n\n- This is a bulleted list item 1\n- This is a bulleted list item 2\n  - This is a nested list item\n\n1. This is a numbered list item 1\n2. This is a numbered list item 2\n\n`This is inline code`\n\n```\nThis is a code block\nwith multiple lines\n```\n\n[This is a link](https://www.example.com)\n\n![This is an image](https://www.example.com/image.jpg)\n```\n\nWould you like an example of Markdown specific to any particular use case?
"""

print(markdown_to_html(md_conetent))