#!/usr/bin/env python3
import re
import html

def markdown_to_medium_html(md_text):
    diagram_map = [
        ("diagram_1_evolution.png", "The Evolution of Compute Isolation: From Bare Metal to In-Container Sandboxes"),
        ("diagram_2_zero_trust_triad.png", "The Zero-Trust Security Triad: Credential, Network, and Filesystem Boundaries"),
        ("diagram_3a_oneshot_mode.png", "Execution Mode 1: One-Shot Lifecycle (sandbox do)"),
        ("diagram_3b_detached_mode.png", "Execution Mode 2: Stateful Background Daemon (sandbox run & exec)"),
        ("diagram_4_storage_options.png", "Filesystem Architecture and Storage Topologies in Cloud Run Sandboxes"),
        ("diagram_5_autograder_sequence.png", "Use Case 1: Automated Coding Assignment Autograder Architecture"),
        ("diagram_6_scraper_architecture.png", "Use Case 2: AI Web Research Scraper with Metadata SSRF Defense"),
        ("diagram_7_detonator_sequence.png", "Use Case 3: SecOps Incident Response & Malware Detonation Sandbox")
    ]

    # Replace mermaid blocks with figure tags pointing to GitHub raw URLs
    mermaid_idx = [0]
    def replace_mermaid(match):
        idx = mermaid_idx[0]
        if idx < len(diagram_map):
            img_name, caption = diagram_map[idx]
            mermaid_idx[0] += 1
            img_url = f"https://raw.githubusercontent.com/rominirani/cloud-run-sandboxes/main/assets/diagrams/{img_name}"
            return f"\n\n[MERMAID_FIGURE:{img_url}|||{caption}]\n\n"
        return ""

    text = re.sub(r"```mermaid.*?```", replace_mermaid, md_text, flags=re.DOTALL)

    # Protect code blocks
    code_blocks = []
    def save_code_block(match):
        lang = match.group(1) or ""
        code = match.group(2)
        idx = len(code_blocks)
        escaped = html.escape(code.rstrip())
        code_blocks.append(f'<pre><code class="language-{lang}">{escaped}</code></pre>')
        return f"\n\n[CODE_BLOCK_{idx}]\n\n"

    text = re.sub(r"```(\w+)?\n(.*?)```", save_code_block, text, flags=re.DOTALL)

    lines = text.splitlines()
    output = []
    in_table = False
    table_rows = []
    in_list = False
    list_type = None # 'ul' or 'ol'
    in_blockquote = False
    blockquote_lines = []

    def flush_blockquote():
        nonlocal in_blockquote, blockquote_lines
        if in_blockquote:
            content = " ".join(blockquote_lines)
            alert_prefix = ""
            for tag, icon in [("[!NOTE]", "💡 Note:"), ("[!TIP]", "⚡ Tip:"), ("[!IMPORTANT]", "⚠️ Important:"), ("[!WARNING]", "🚨 Warning:")]:
                if content.startswith(tag):
                    content = content[len(tag):].strip()
                    alert_prefix = f"<strong>{icon}</strong> "
                    break
            output.append(f"<blockquote><p>{alert_prefix}{parse_inline(content)}</p></blockquote>")
            in_blockquote = False
            blockquote_lines = []

    def flush_list():
        nonlocal in_list, list_type
        if in_list:
            output.append(f"</{list_type}>")
            in_list = False
            list_type = None

    def flush_table():
        nonlocal in_table, table_rows
        if in_table:
            if len(table_rows) >= 2:
                # header
                headers = [c.strip() for c in table_rows[0].strip("|").split("|")]
                # separator is table_rows[1]
                tbody_rows = []
                for row in table_rows[2:]:
                    cells = [c.strip() for c in row.strip("|").split("|")]
                    td_html = "".join(f"<td>{parse_inline(c)}</td>" for c in cells)
                    tbody_rows.append(f"<tr>{td_html}</tr>")
                
                th_html = "".join(f"<th>{parse_inline(h)}</th>" for h in headers)
                table_html = f"""<div class="table-container"><table>
<thead><tr>{th_html}</tr></thead>
<tbody>{"".join(tbody_rows)}</tbody>
</table></div>"""
                output.append(table_html)
            in_table = False
            table_rows = []

    def parse_inline(s):
        # Links
        s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
        # Bold
        s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
        # Italic
        s = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', s)
        # Inline code
        s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
        return s

    for line in lines:
        stripped = line.strip()

        # Check for Mermaid placeholders
        if stripped.startswith("[MERMAID_FIGURE:") and stripped.endswith("]"):
            flush_blockquote()
            flush_list()
            flush_table()
            payload = stripped[16:-1]
            parts = payload.split("|||", 1)
            img_url = parts[0]
            caption = parts[1] if len(parts) > 1 else ""
            fig = f"""<figure>
  <img src="{img_url}" alt="{caption}">
  <figcaption>{caption}</figcaption>
</figure>"""
            output.append(fig)
            continue

        # Check for Code block placeholders
        if stripped.startswith("[CODE_BLOCK_") and stripped.endswith("]"):
            flush_blockquote()
            flush_list()
            flush_table()
            idx = int(stripped[12:-1])
            output.append(code_blocks[idx])
            continue

        # Tables
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_blockquote()
            flush_list()
            in_table = True
            table_rows.append(stripped)
            continue
        else:
            flush_table()

        # Blockquote
        if stripped.startswith(">"):
            flush_list()
            in_blockquote = True
            quote_text = stripped.lstrip("> ").strip()
            blockquote_lines.append(quote_text)
            continue
        else:
            flush_blockquote()

        # Unordered list
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list or list_type != "ul":
                flush_list()
                in_list = True
                list_type = "ul"
                output.append("<ul>")
            item_text = stripped[2:].strip()
            output.append(f"<li>{parse_inline(item_text)}</li>")
            continue

        # Ordered list
        m_ol = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        if m_ol:
            if not in_list or list_type != "ol":
                flush_list()
                in_list = True
                list_type = "ol"
                output.append("<ol>")
            item_text = m_ol.group(2).strip()
            output.append(f"<li>{parse_inline(item_text)}</li>")
            continue

        flush_list()

        # Empty lines
        if not stripped:
            continue

        # Horizontal Rule
        if stripped in ("---", "***", "___"):
            output.append("<hr>")
            continue

        # Headings
        if stripped.startswith("# "):
            output.append(f"<h1>{parse_inline(stripped[2:].strip())}</h1>")
            continue
        elif stripped.startswith("## "):
            output.append(f"<h2>{parse_inline(stripped[3:].strip())}</h2>")
            continue
        elif stripped.startswith("### "):
            output.append(f"<h3>{parse_inline(stripped[4:].strip())}</h3>")
            continue
        elif stripped.startswith("#### "):
            output.append(f"<h4>{parse_inline(stripped[5:].strip())}</h4>")
            continue

        # Regular Paragraph
        output.append(f"<p>{parse_inline(stripped)}</p>")

    flush_blockquote()
    flush_list()
    flush_table()

    body_content = "\n".join(output)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Getting Started with Google Cloud Run Sandboxes</title>
  <meta name="description" content="A Hands-On Guide to Safely Running Untrusted Code and AI Agent Workloads">
  <style>
    :root {{
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
      --font-serif: "Charter", "Bitstream Charter", "Sitka Text", Cambria, serif;
      --font-mono: "Menlo", "Monaco", "Courier New", monospace;
      --color-text: #242424;
      --color-bg: #ffffff;
      --color-accent: #1a8917;
      --color-border: #e6e6e6;
      --color-code-bg: #f9f9f9;
    }}

    body {{
      font-family: var(--font-serif);
      color: var(--color-text);
      background-color: var(--color-bg);
      line-height: 1.75;
      font-size: 20px;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
    }}

    /* Copy to Medium Helper Bar */
    .medium-helper-bar {{
      position: sticky;
      top: 0;
      background: #fbfbfb;
      border-bottom: 1px solid #e0e0e0;
      padding: 16px 24px;
      font-family: var(--font-sans);
      font-size: 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 8px rgba(0,0,0,0.04);
      z-index: 1000;
    }}

    .medium-helper-bar strong {{
      color: #1a8917;
    }}

    .btn-copy {{
      background: #1a8917;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 20px;
      cursor: pointer;
      font-weight: 500;
      font-size: 14px;
    }}

    .btn-copy:hover {{
      background: #156d12;
    }}

    .article-container {{
      max-width: 740px;
      margin: 40px auto 100px auto;
      padding: 0 24px;
    }}

    h1 {{
      font-family: var(--font-sans);
      font-size: 42px;
      font-weight: 700;
      line-height: 1.2;
      margin-top: 40px;
      margin-bottom: 12px;
      letter-spacing: -0.02em;
    }}

    h2 {{
      font-family: var(--font-sans);
      font-size: 30px;
      font-weight: 700;
      line-height: 1.3;
      margin-top: 56px;
      margin-bottom: 16px;
      letter-spacing: -0.015em;
    }}

    h3 {{
      font-family: var(--font-sans);
      font-size: 24px;
      font-weight: 600;
      line-height: 1.4;
      margin-top: 36px;
      margin-bottom: 12px;
    }}

    h4 {{
      font-family: var(--font-sans);
      font-size: 20px;
      font-weight: 600;
      margin-top: 28px;
      margin-bottom: 8px;
    }}

    p {{
      margin-top: 0;
      margin-bottom: 24px;
    }}

    a {{
      color: inherit;
      text-decoration: underline;
    }}

    figure {{
      margin: 44px 0;
      text-align: center;
    }}

    figure img {{
      max-width: 100%;
      height: auto;
      border-radius: 4px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    }}

    figcaption {{
      font-family: var(--font-sans);
      font-size: 14px;
      color: #757575;
      margin-top: 10px;
      font-style: italic;
    }}

    blockquote {{
      border-left: 3px solid #242424;
      margin: 32px 0;
      padding-left: 20px;
      font-style: italic;
      color: #242424;
    }}

    pre {{
      background-color: var(--color-code-bg);
      border-radius: 4px;
      padding: 16px 20px;
      overflow-x: auto;
      font-family: var(--font-mono);
      font-size: 15px;
      line-height: 1.5;
      margin: 32px 0;
      border: 1px solid #eeeeee;
    }}

    code {{
      font-family: var(--font-mono);
      font-size: 0.85em;
      background-color: rgba(0, 0, 0, 0.05);
      padding: 2px 6px;
      border-radius: 3px;
    }}

    pre code {{
      background-color: transparent;
      padding: 0;
      font-size: 14px;
    }}

    ul, ol {{
      margin-top: 0;
      margin-bottom: 28px;
      padding-left: 30px;
    }}

    li {{
      margin-bottom: 8px;
    }}

    hr {{
      border: none;
      border-top: 1px solid #e6e6e6;
      margin: 48px 0;
    }}

    .table-container {{
      overflow-x: auto;
      margin: 32px 0;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-family: var(--font-sans);
      font-size: 16px;
    }}

    th, td {{
      padding: 12px 16px;
      text-align: left;
      border-bottom: 1px solid #e6e6e6;
    }}

    th {{
      font-weight: 600;
      background-color: #fafafa;
    }}
  </style>
</head>
<body>

  <div class="medium-helper-bar">
    <div>
      <strong>Ready for Medium!</strong> Select all (<code>Cmd+A</code>) &amp; copy (<code>Cmd+C</code>), then paste directly into <a href="https://medium.com/new-story" target="_blank">Medium</a>.
    </div>
    <button class="btn-copy" onclick="copyArticleContent()">Copy Story Content</button>
  </div>

  <div class="article-container" id="article-content">
{body_content}
  </div>

  <script>
    function copyArticleContent() {{
      const container = document.getElementById('article-content');
      const range = document.createRange();
      range.selectNode(container);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
      try {{
        document.execCommand('copy');
        alert('Copied to clipboard! Go to Medium (medium.com/new-story) and press Cmd+V / Ctrl+V to paste.');
      }} catch (err) {{
        alert('Please manually select all text on the page and press Cmd+C to copy.');
      }}
      window.getSelection().removeAllRanges();
    }}
  </script>
</body>
</html>"""
    return full_html

if __name__ == "__main__":
    with open("TUTORIAL.md", "r") as f:
        md = f.read()
    html_out = markdown_to_medium_html(md)
    with open("medium-post.html", "w") as f:
        f.write(html_out)
    print("Successfully generated medium-post.html!")
