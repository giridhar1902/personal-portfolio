import os
import subprocess
import markdown

md_path = r"d:\personal-portfolio\cold-outreach-recipient-intelligence\synthesis\cold-outreach-playbook-sop.md"
html_path = r"d:\personal-portfolio\cold-outreach-recipient-intelligence\synthesis\temp_playbook.html"
pdf_root_path = r"d:\personal-portfolio\cold-outreach-playbook-sop.pdf"
pdf_synthesis_path = r"d:\personal-portfolio\cold-outreach-recipient-intelligence\synthesis\cold-outreach-playbook-sop.pdf"

with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

# Convert markdown to html with table and code extensions
html_body = markdown.markdown(
    md_content,
    extensions=['tables', 'fenced_code', 'toc', 'nl2br', 'sane_lists']
)

# Custom high-end PDF CSS stylesheet
css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

@page {
    size: A4;
    margin: 20mm 18mm 20mm 18mm;
    @bottom-right {
        content: counter(page);
    }
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1e293b;
    line-height: 1.6;
    font-size: 10.5pt;
    background-color: #ffffff;
}

h1 {
    font-size: 22pt;
    font-weight: 800;
    color: #0f172a;
    border-bottom: 3px solid #2563eb;
    padding-bottom: 8px;
    margin-top: 0;
    margin-bottom: 24px;
    letter-spacing: -0.02em;
}

h2 {
    font-size: 15pt;
    font-weight: 700;
    color: #1e293b;
    border-bottom: 1.5px solid #cbd5e1;
    padding-bottom: 5px;
    margin-top: 28px;
    margin-bottom: 14px;
    page-break-after: avoid;
}

h3 {
    font-size: 12.5pt;
    font-weight: 600;
    color: #2563eb;
    margin-top: 20px;
    margin-bottom: 10px;
    page-break-after: avoid;
}

h4 {
    font-size: 11pt;
    font-weight: 600;
    color: #334155;
    margin-top: 16px;
    margin-bottom: 8px;
    page-break-after: avoid;
}

p {
    margin-top: 0;
    margin-bottom: 12px;
    text-align: justify;
}

ul, ol {
    margin-top: 0;
    margin-bottom: 14px;
    padding-left: 22px;
}

li {
    margin-bottom: 6px;
}

blockquote {
    border-left: 4px solid #2563eb;
    background-color: #f0f9ff;
    color: #1e3a8a;
    padding: 10px 16px;
    margin: 14px 0;
    border-radius: 0 6px 6px 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}

blockquote p {
    margin: 0;
    text-align: left;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 18px 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}

th {
    background-color: #0f172a;
    color: #ffffff;
    font-weight: 600;
    text-align: left;
    padding: 9px 12px;
    border: 1px solid #0f172a;
}

td {
    padding: 8px 12px;
    border: 1px solid #e2e8f0;
    vertical-align: top;
}

tr:nth-child(even) td {
    background-color: #f8fafc;
}

code {
    font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
    font-size: 9pt;
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 2px 6px;
    border-radius: 4px;
}

pre {
    background-color: #0f172a;
    color: #f8fafc;
    padding: 14px 18px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.45;
    margin: 16px 0;
    page-break-inside: avoid;
}

pre code {
    background-color: transparent;
    color: inherit;
    padding: 0;
}

hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 24px 0;
}

a {
    color: #2563eb;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

.header-tag {
    display: inline-block;
    background-color: #dbeafe;
    color: #1e40af;
    font-weight: 600;
    font-size: 8.5pt;
    padding: 4px 10px;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
}
"""

full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>The B2B SaaS Cold Outreach Playbook & SOP</title>
    <style>
    {css}
    </style>
</head>
<body>
    <div class="header-tag">Standard Operating Procedure • B2B SaaS GTM</div>
    {html_body}
</body>
</html>
"""

with open(html_path, "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"Generated HTML at {html_path}")

# Run Edge headless to convert HTML to PDF
edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
cmd = [
    edge_path,
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={pdf_root_path}",
    html_path
]

res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode == 0 and os.path.exists(pdf_root_path):
    print(f"Successfully generated PDF at {pdf_root_path}")
    # Also save copy in synthesis directory
    with open(pdf_root_path, "rb") as src, open(pdf_synthesis_path, "wb") as dst:
        dst.write(src.read())
    print(f"Successfully copied PDF to {pdf_synthesis_path}")
else:
    print(f"Error generating PDF: {res.stderr}")
