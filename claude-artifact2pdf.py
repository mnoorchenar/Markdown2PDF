from flask import Flask, render_template_string, request, send_file
import markdown
from io import BytesIO
import re
from xhtml2pdf import pisa
app = Flask(__name__)
def generate_css(settings):
    """Generate CSS based on user settings"""
   
    # Calculate heading sizes based on base font
    base_size = settings['base_font_size']
    h1_size = base_size * 2
    h2_size = base_size * 1.4
    h3_size = base_size * 1.2
   
    # Code box border style
    code_border = f"border: 1px solid {settings['code_border_color']};" if settings['show_code_border'] else "border: none;"
    code_border_left = f"border-left: 3px solid {settings['code_accent_color']};" if settings['show_code_border'] else ""
   
    # PDF page size
    page_size = settings['page_size']
   
    return f'''
        @page {{
            size: {page_size};
            margin: {settings['page_margin']}cm;
        }}
       
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
       
        body {{
            font-family: Georgia, serif;
            line-height: 1.5;
            color: #1a1a1a;
            font-size: {settings['base_font_size']}pt;
        }}
       
        h1 {{
            color: #2c3e50;
            font-size: {h1_size}pt;
            margin-bottom: 15px;
            margin-top: 0;
            padding-bottom: 8px;
            border-bottom: 2px solid #3498db;
            page-break-after: avoid;
            background-color: transparent;
        }}
       
        h2 {{
            color: #34495e;
            font-size: {h2_size}pt;
            margin-top: 20px;
            margin-bottom: 10px;
            padding-top: 5px;
            border-top: 1px solid #ecf0f1;
            page-break-after: avoid;
            background-color: transparent;
        }}
       
        h3 {{
            color: #555;
            font-size: {h3_size}pt;
            margin-top: 15px;
            margin-bottom: 8px;
            page-break-after: avoid;
            background-color: transparent;
        }}
       
        h4 {{
            color: #666;
            font-size: {base_size}pt;
            margin-top: 12px;
            margin-bottom: 6px;
            background-color: transparent;
        }}
       
        p {{
            margin-bottom: {settings['paragraph_spacing']}px;
            text-align: justify;
            background-color: transparent;
        }}
       
        strong {{
            color: #2c3e50;
            font-weight: 600;
            background-color: transparent;
        }}
       
        code {{
            background-color: transparent;
            padding: 0;
            border-radius: 0;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: {settings['base_font_size']}pt;
            color: #000000;
        }}
       
        /* Code blocks */
        pre {{
            background-color: {settings['code_bg_color']};
            {code_border}
            {code_border_left}
            padding: {settings['code_padding_vertical']}px {settings['code_padding_horizontal']}px;
            margin: {settings['code_margin_top']}px 0 {settings['code_margin_bottom']}px 0;
            overflow-x: auto;
            border-radius: 3px;
            page-break-inside: avoid;
        }}
       
        pre code {{
            background-color: transparent;
            padding: 0;
            color: #000000;
            font-size: {settings['code_font_size']}pt;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            display: block;
            line-height: 1.4;
            white-space: pre;
        }}
       
        /* SQL Syntax Highlighting */
        .sql-keyword {{
            color: {settings['keyword_color']};
            font-weight: bold;
        }}
       
        .sql-comment {{
            color: {settings['comment_color']};
            font-style: italic;
        }}
       
        .sql-string {{
            color: {settings['string_color']};
        }}
       
        .sql-number {{
            color: {settings['number_color']};
        }}
       
        .sql-function {{
            color: {settings['function_color']};
            font-weight: bold;
        }}
       
        /* Python Syntax Highlighting */
        .py-keyword {{
            color: {settings['keyword_color']};
            font-weight: bold;
        }}
       
        .py-string {{
            color: {settings['string_color']};
        }}
       
        .py-number {{
            color: {settings['number_color']};
        }}
       
        .py-comment {{
            color: {settings['comment_color']};
            font-style: italic;
        }}
       
        .py-function {{
            color: {settings['function_color']};
        }}
       
        .py-builtin {{
            color: {settings['keyword_color']};
        }}
       
        .py-decorator {{
            color: #808080;
        }}
       
        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: {settings['base_font_size'] - 1}pt;
            page-break-inside: avoid;
        }}
       
        table th {{
            background-color: #3498db;
            color: white;
            padding: 5px 8px;
            text-align: left;
            font-weight: 600;
            border: 1px solid #2980b9;
            line-height: 1.2;
        }}
       
        table td {{
            border: 1px solid #ddd;
            padding: 4px 8px;
            vertical-align: top;
            line-height: 1.2;
        }}
       
        table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
       
        /* Lists */
        ul, ol {{
            margin-left: 25px;
            margin-bottom: 10px;
        }}
       
        li {{
            margin-bottom: 4px;
            line-height: 1.4;
        }}
       
        blockquote {{
            border-left: 3px solid #3498db;
            padding: 8px 12px;
            margin: 10px 0;
            color: #555;
            font-style: italic;
            background-color: #f8f9fa;
        }}
       
        hr {{
            border: none;
            border-top: 1px solid #ecf0f1;
            margin: 15px 0;
        }}
       
        /* Callout boxes */
        .warning {{
            background-color: #fff3cd;
            border-left: 3px solid #ffc107;
            padding: 8px 12px;
            margin: 10px 0;
            border-radius: 3px;
        }}
       
        .success {{
            background-color: #d4edda;
            border-left: 3px solid #28a745;
            padding: 8px 12px;
            margin: 10px 0;
            border-radius: 3px;
        }}
       
        .error {{
            background-color: #f8d7da;
            border-left: 3px solid #dc3545;
            padding: 8px 12px;
            margin: 10px 0;
            border-radius: 3px;
        }}
       
        .info {{
            background-color: #d1ecf1;
            border-left: 3px solid #0c5460;
            padding: 8px 12px;
            margin: 10px 0;
            border-radius: 3px;
        }}
    '''
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Document</title>
    <style>
        {{ css|safe }}
    </style>
</head>
<body>
    {{ content|safe }}
</body>
</html>
'''
def highlight_sql(code):
    """LaTeX-quality SQL syntax highlighting"""
   
    keywords = [
        'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER',
        'TABLE', 'DATABASE', 'INDEX', 'VIEW', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
        'FULL', 'CROSS', 'ON', 'USING', 'AS', 'AND', 'OR', 'NOT', 'NULL', 'IS', 'IN',
        'BETWEEN', 'LIKE', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'DISTINCT',
        'UNION', 'ALL', 'INTERSECT', 'EXCEPT', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE',
        'END', 'IF', 'WITH', 'RECURSIVE', 'ASC', 'DESC', 'INTO', 'VALUES', 'SET', 'DEFAULT',
        'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'CONSTRAINT', 'UNIQUE', 'CHECK',
        'AUTO_INCREMENT', 'SERIAL', 'AUTOINCREMENT', 'IDENTITY', 'RETURNS', 'BEGIN',
        'COMMIT', 'ROLLBACK', 'TRANSACTION', 'GRANT', 'REVOKE', 'CASCADE', 'RESTRICT',
        'INT', 'INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT', 'DECIMAL', 'NUMERIC', 'FLOAT',
        'REAL', 'DOUBLE', 'VARCHAR', 'CHAR', 'TEXT', 'BLOB', 'DATE', 'TIME', 'DATETIME',
        'TIMESTAMP', 'BOOLEAN', 'BOOL', 'ENUM', 'JSON', 'ARRAY'
    ]
   
    functions = [
        'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'CONCAT', 'UPPER', 'LOWER', 'LENGTH',
        'SUBSTRING', 'TRIM', 'ROUND', 'FLOOR', 'CEIL', 'ABS', 'NOW', 'CURRENT_DATE',
        'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'DATE', 'TIME', 'YEAR', 'MONTH', 'DAY',
        'COALESCE', 'NULLIF', 'CAST', 'CONVERT'
    ]
   
    result = code
   
    # Protect comments
    comment_placeholder = {}
    comment_counter = 0
   
    for match in re.finditer(r'--[^\n]*', result):
        placeholder = f'___COMMENT_{comment_counter}___'
        comment_placeholder[placeholder] = f'<span class="sql-comment">{match.group(0)}</span>'
        result = result.replace(match.group(0), placeholder, 1)
        comment_counter += 1
   
    for match in re.finditer(r'/\*.*?\*/', result, re.DOTALL):
        placeholder = f'___COMMENT_{comment_counter}___'
        comment_placeholder[placeholder] = f'<span class="sql-comment">{match.group(0)}</span>'
        result = result.replace(match.group(0), placeholder, 1)
        comment_counter += 1
   
    # Protect strings
    string_placeholder = {}
    string_counter = 0
   
    for match in re.finditer(r"'(?:[^'\\]|\\.)*'", result):
        placeholder = f'___STRING_{string_counter}___'
        string_placeholder[placeholder] = f'<span class="sql-string">{match.group(0)}</span>'
        result = result.replace(match.group(0), placeholder, 1)
        string_counter += 1
   
    # Highlight numbers
    result = re.sub(r'\b(\d+\.?\d*)\b', r'<span class="sql-number">\1</span>', result)
   
    # Highlight functions
    for func in functions:
        result = re.sub(
            r'\b(' + func + r')\s*\(',
            r'<span class="sql-function">\1</span>(',
            result,
            flags=re.IGNORECASE
        )
   
    # Highlight keywords
    for keyword in keywords:
        result = re.sub(
            r'\b(' + keyword + r')\b',
            r'<span class="sql-keyword">\1</span>',
            result,
            flags=re.IGNORECASE
        )
   
    # Restore strings and comments
    for placeholder, original in string_placeholder.items():
        result = result.replace(placeholder, original)
   
    for placeholder, original in comment_placeholder.items():
        result = result.replace(placeholder, original)
   
    return result
def highlight_python(code):
    """LaTeX-quality Python syntax highlighting"""
   
    keywords = [
        'def', 'class', 'import', 'from', 'as', 'if', 'elif', 'else', 'for', 'while',
        'return', 'try', 'except', 'finally', 'with', 'lambda', 'yield', 'async', 'await',
        'pass', 'break', 'continue', 'and', 'or', 'not', 'in', 'is', 'None', 'True', 'False',
        'raise', 'assert', 'del', 'global', 'nonlocal'
    ]
   
    builtins = [
        'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple',
        'open', 'input', 'type', 'isinstance', 'enumerate', 'zip', 'map', 'filter', 'sum',
        'max', 'min', 'sorted', 'reversed', 'all', 'any', 'abs', 'round', 'pow'
    ]
   
    result = code
   
    # Protect comments
    comment_placeholder = {}
    comment_counter = 0
   
    for match in re.finditer(r'#[^\n]*', result):
        placeholder = f'___COMMENT_{comment_counter}___'
        comment_placeholder[placeholder] = f'<span class="py-comment">{match.group(0)}</span>'
        result = result.replace(match.group(0), placeholder, 1)
        comment_counter += 1
   
    # Protect strings
    string_placeholder = {}
    string_counter = 0
   
    for match in re.finditer(r'"""(?:[^"\\]|\\.)*?"""|\'\'\'(?:[^\'\\]|\\.)*?\'\'\'', result, re.DOTALL):
        placeholder = f'___STRING_{string_counter}___'
        string_placeholder[placeholder] = f'<span class="py-string">{match.group(0)}</span>'
        result = result.replace(match.group(0), placeholder, 1)
        string_counter += 1
   
    for match in re.finditer(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', result):
        placeholder = f'___STRING_{string_counter}___'
        string_placeholder[placeholder] = f'<span class="py-string">{match.group(0)}</span>'
        result = result.replace(match.group(0), placeholder, 1)
        string_counter += 1
   
    # Highlight decorators
    result = re.sub(r'(@\w+)', r'<span class="py-decorator">\1</span>', result)
   
    # Highlight numbers
    result = re.sub(r'\b(\d+\.?\d*)\b', r'<span class="py-number">\1</span>', result)
   
    # Highlight keywords
    for keyword in keywords:
        result = re.sub(r'\b(' + keyword + r')\b', r'<span class="py-keyword">\1</span>', result)
   
    # Highlight builtins
    for builtin in builtins:
        result = re.sub(r'\b(' + builtin + r')\b', r'<span class="py-builtin">\1</span>', result)
   
    # Restore strings and comments
    for placeholder, original in string_placeholder.items():
        result = result.replace(placeholder, original)
   
    for placeholder, original in comment_placeholder.items():
        result = result.replace(placeholder, original)
   
    return result
def process_code_blocks(md_text):
    """Process all code blocks in markdown"""
   
    def replace_code_block(match):
        lang = match.group(1) if match.group(1) else ''
        code = match.group(2).strip('\n')
        lang_lower = lang.lower().strip()
       
        if lang_lower in ['sql', 'mysql', 'postgresql', 'postgres', 'sqlite', 'tsql', 'plsql']:
            highlighted = highlight_sql(code)
        elif lang_lower in ['python', 'py', 'python3']:
            highlighted = highlight_python(code)
        else:
            highlighted = code
       
        return f'<pre><code>{highlighted}</code></pre>'
   
    result = re.sub(r'```([a-zA-Z0-9]*)\n(.*?)\n```', replace_code_block, md_text, flags=re.DOTALL)
    result = re.sub(r'```([a-zA-Z0-9]*)\n(.*?)```', replace_code_block, result, flags=re.DOTALL)
    result = re.sub(r'```\s*([a-zA-Z0-9]*)\s*\n(.*?)```', replace_code_block, result, flags=re.DOTALL)
   
    return result
def process_markdown(md_text):
    """Convert markdown to HTML with syntax highlighting"""
    md_with_highlighted_code = process_code_blocks(md_text)
    html = markdown.markdown(md_with_highlighted_code, extensions=['tables', 'fenced_code'])
    html = re.sub(r'style="[^"]*"', '', html)
   
    html = re.sub(r'<p><strong>⚠️[^<]*</strong>', r'<div class="warning"><strong>⚠️ Warning:</strong>', html)
    html = re.sub(r'<p><strong>✓[^<]*</strong>', r'<div class="success"><strong>✓ Best Practice:</strong>', html)
    html = re.sub(r'<p><strong>✗[^<]*</strong>', r'<div class="error"><strong>✗ Common Mistake:</strong>', html)
    html = re.sub(r'<p><strong>💡[^<]*</strong>', r'<div class="info"><strong>💡 Info:</strong>', html)
   
    return html
@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Markdown to PDF Converter</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            padding: 20px;
            overflow: hidden;
            margin: 0;
        }
        .container {
            max-width: 1400px;
            height: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 5px;
            font-size: 2em;
        }
        .subtitle {
            color: #7f8c8d;
            margin-bottom: 15px;
            font-size: 1em;
        }
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 350px;
            gap: 25px;
            flex: 1;
            overflow: hidden;
            min-height: 0;
        }
        .textarea-wrapper {
            display: flex;
            flex-direction: column;
            overflow: hidden;
            min-height: 0;
        }
        textarea {
            width: 100%;
            flex: 1;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-family: 'Consolas', monospace;
            font-size: 13px;
            resize: none;
            line-height: 1.5;
            overflow-y: auto;
            min-height: 0;
        }
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .settings-panel {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            overflow-y: auto;
            overflow-x: hidden;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }
        .settings-panel h3 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.1em;
            position: sticky;
            top: 0;
            background: #f8f9fa;
            padding: 5px 0;
            z-index: 10;
        }
        .section {
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #dee2e6;
        }
        .section:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        .section h4 {
            color: #495057;
            font-size: 0.95em;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .field {
            margin-bottom: 12px;
        }
        .field label {
            display: block;
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
            font-weight: 500;
        }
        .field input[type="number"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            font-size: 0.9em;
        }
        .field input[type="color"] {
            width: 100%;
            height: 40px;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            cursor: pointer;
        }
        .field input:focus {
            outline: none;
            border-color: #667eea;
        }
        .checkbox-field {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }
        .checkbox-field input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        .checkbox-field label {
            color: #666;
            font-size: 0.9em;
            margin: 0;
            cursor: pointer;
        }
        .btn-generate {
            width: 100%;
            padding: 15px;
            margin-top: 15px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 1px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            transition: all 0.3s;
            flex-shrink: 0;
        }
        .btn-generate:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        .preset-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 20px;
        }
        .btn-preset {
            padding: 10px;
            font-size: 13px;
            font-weight: 600;
            border: 2px solid #28a745;
            border-radius: 8px;
            cursor: pointer;
            background: white;
            color: #28a745;
            transition: all 0.3s;
        }
        .btn-preset:hover {
            background: #28a745;
            color: white;
        }
        .btn-preset.compact {
            border-color: #17a2b8;
            color: #17a2b8;
        }
        .btn-preset.compact:hover {
            background: #17a2b8;
        }
        form {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            min-height: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 Markdown to PDF Converter</h1>
        <p class="subtitle">Simplified settings with full color customization</p>
       
        <form method="POST" action="/generate">
            <div class="main-grid">
                <!-- Markdown Input -->
                <div class="textarea-wrapper">
                    <textarea name="markdown" placeholder="Paste your markdown content here...
# SQL Example
```sql
-- Select products
SELECT name, price
FROM products
WHERE price > 100;
```"></textarea>
                    <button type="submit" class="btn-generate">Generate PDF</button>
                </div>
               
                <!-- Settings Panel -->
                <div class="settings-panel">
                    <h3>⚙️ PDF Settings</h3>
                   
                    <!-- Presets -->
                    <div class="preset-grid">
                        <button type="button" class="btn-preset" onclick="applyDefault()">Default</button>
                        <button type="button" class="btn-preset compact" onclick="applyCompact()">Compact</button>
                    </div>
                   
                    <!-- Font Sizes -->
                    <div class="section">
                        <h4>📝 Font Sizes</h4>
                        <div class="field">
                            <label>Text Size (pt)</label>
                            <input type="number" name="base_font_size" value="10" step="0.5" min="7" max="14">
                        </div>
                        <div class="field">
                            <label>Code Size (pt)</label>
                            <input type="number" name="code_font_size" value="7.5" step="0.5" min="6" max="12">
                        </div>
                    </div>
                   
                    <!-- Page Settings -->
                    <div class="section">
                        <h4>📄 Page Settings</h4>
                        <div class="field">
                            <label>Page Size</label>
                            <select name="page_size" style="width: 100%; padding: 8px; border: 1px solid #dee2e6; border-radius: 5px; font-size: 0.9em;">
                                <option value="A4">A4 (21cm × 29.7cm)</option>
                                <option value="Letter">Letter (21.6cm × 27.9cm)</option>
                                <option value="Legal">Legal (21.6cm × 35.6cm)</option>
                                <option value="A3">A3 (29.7cm × 42cm)</option>
                            </select>
                        </div>
                        <div class="field">
                            <label>Page Margin (cm)</label>
                            <input type="number" name="page_margin" value="1.5" step="0.1" min="0.5" max="4">
                        </div>
                    </div>
                   
                    <!-- Spacing -->
                    <div class="section">
                        <h4>📐 Spacing</h4>
                        <div class="field">
                            <label>Paragraph Spacing (px)</label>
                            <input type="number" name="paragraph_spacing" value="8" step="1" min="4" max="20">
                        </div>
                        <div class="field">
                            <label>Code Padding - Top/Bottom (px)</label>
                            <input type="number" name="code_padding_vertical" value="15" step="1" min="8" max="40">
                        </div>
                        <div class="field">
                            <label>Code Padding - Left/Right (px)</label>
                            <input type="number" name="code_padding_horizontal" value="12" step="1" min="8" max="40">
                        </div>
                        <div class="field">
                            <label>Code Margin - Top (px)</label>
                            <input type="number" name="code_margin_top" value="15" step="1" min="8" max="40">
                        </div>
                        <div class="field">
                            <label>Code Margin - Bottom (px)</label>
                            <input type="number" name="code_margin_bottom" value="15" step="1" min="8" max="40">
                        </div>
                    </div>
                   
                    <!-- Code Box Style -->
                    <div class="section">
                        <h4>📦 Code Box Style</h4>
                        <div class="checkbox-field">
                            <input type="checkbox" id="show_border" name="show_code_border" value="yes" checked>
                            <label for="show_border">Show Border</label>
                        </div>
                        <div class="field">
                            <label>Background Color</label>
                            <input type="color" name="code_bg_color" value="#f5f5f5">
                        </div>
                        <div class="field">
                            <label>Border Color</label>
                            <input type="color" name="code_border_color" value="#dddddd">
                        </div>
                        <div class="field">
                            <label>Accent Color (left bar)</label>
                            <input type="color" name="code_accent_color" value="#3498db">
                        </div>
                    </div>
                   
                    <!-- Syntax Colors -->
                    <div class="section">
                        <h4>🎨 Syntax Highlighting</h4>
                        <div class="field">
                            <label>Keywords (SELECT, def, class)</label>
                            <input type="color" name="keyword_color" value="#0000ff">
                        </div>
                        <div class="field">
                            <label>Strings ('text', "text")</label>
                            <input type="color" name="string_color" value="#ff8c00">
                        </div>
                        <div class="field">
                            <label>Comments (-- , #)</label>
                            <input type="color" name="comment_color" value="#006400">
                        </div>
                        <div class="field">
                            <label>Numbers (123, 45.67)</label>
                            <input type="color" name="number_color" value="#098658">
                        </div>
                        <div class="field">
                            <label>Functions (COUNT, SUM)</label>
                            <input type="color" name="function_color" value="#795e26">
                        </div>
                    </div>
                </div>
            </div>
        </form>
    </div>
   
    <script>
        function applyDefault() {
            document.querySelector('[name="base_font_size"]').value = 10;
            document.querySelector('[name="code_font_size"]').value = 7.5;
            document.querySelector('[name="page_size"]').value = "A4";
            document.querySelector('[name="page_margin"]').value = 1.5;
            document.querySelector('[name="paragraph_spacing"]').value = 8;
            document.querySelector('[name="code_padding_vertical"]').value = 15;
            document.querySelector('[name="code_padding_horizontal"]').value = 12;
            document.querySelector('[name="code_margin_top"]').value = 15;
            document.querySelector('[name="code_margin_bottom"]').value = 15;
            document.querySelector('[name="show_code_border"]').checked = true;
            document.querySelector('[name="code_bg_color"]').value = "#f5f5f5";
            document.querySelector('[name="code_border_color"]').value = "#dddddd";
            document.querySelector('[name="code_accent_color"]').value = "#3498db";
            document.querySelector('[name="keyword_color"]').value = "#0000ff";
            document.querySelector('[name="string_color"]').value = "#ff8c00";
            document.querySelector('[name="comment_color"]').value = "#006400";
            document.querySelector('[name="number_color"]').value = "#098658";
            document.querySelector('[name="function_color"]').value = "#795e26";
        }
       
        function applyCompact() {
            document.querySelector('[name="base_font_size"]').value = 9;
            document.querySelector('[name="code_font_size"]').value = 7;
            document.querySelector('[name="page_size"]').value = "A4";
            document.querySelector('[name="page_margin"]').value = 1.0;
            document.querySelector('[name="paragraph_spacing"]').value = 5;
            document.querySelector('[name="code_padding_vertical"]').value = 10;
            document.querySelector('[name="code_padding_horizontal"]').value = 10;
            document.querySelector('[name="code_margin_top"]').value = 10;
            document.querySelector('[name="code_margin_bottom"]').value = 10;
            document.querySelector('[name="show_code_border"]').checked = true;
            document.querySelector('[name="code_bg_color"]').value = "#f5f5f5";
            document.querySelector('[name="code_border_color"]').value = "#dddddd";
            document.querySelector('[name="code_accent_color"]').value = "#3498db";
            document.querySelector('[name="keyword_color"]').value = "#0000ff";
            document.querySelector('[name="string_color"]').value = "#ff8c00";
            document.querySelector('[name="comment_color"]').value = "#006400";
            document.querySelector('[name="number_color"]').value = "#098658";
            document.querySelector('[name="function_color"]').value = "#795e26";
        }
    </script>
</body>
</html>
    ''')
@app.route('/generate', methods=['POST'])
def generate_pdf():
    markdown_text = request.form.get('markdown', '')
   
    if not markdown_text:
        return "No markdown content provided", 400
   
    # Get settings from form
    settings = {
        'base_font_size': float(request.form.get('base_font_size', 10)),
        'code_font_size': float(request.form.get('code_font_size', 7.5)),
        'page_size': request.form.get('page_size', 'A4'),
        'page_margin': float(request.form.get('page_margin', 1.5)),
        'paragraph_spacing': int(request.form.get('paragraph_spacing', 8)),
        'code_padding_vertical': int(request.form.get('code_padding_vertical', 15)),
        'code_padding_horizontal': int(request.form.get('code_padding_horizontal', 12)),
        'code_margin_top': int(request.form.get('code_margin_top', 15)),
        'code_margin_bottom': int(request.form.get('code_margin_bottom', 15)),
        'show_code_border': request.form.get('show_code_border') == 'yes',
        'code_bg_color': request.form.get('code_bg_color', '#f5f5f5'),
        'code_border_color': request.form.get('code_border_color', '#dddddd'),
        'code_accent_color': request.form.get('code_accent_color', '#3498db'),
        'keyword_color': request.form.get('keyword_color', '#0000ff'),
        'string_color': request.form.get('string_color', '#ff8c00'),
        'comment_color': request.form.get('comment_color', '#006400'),
        'number_color': request.form.get('number_color', '#098658'),
        'function_color': request.form.get('function_color', '#795e26'),
    }
   
    # Generate CSS with user settings
    css = generate_css(settings)
   
    # Convert markdown to HTML
    content_html = process_markdown(markdown_text)
   
    # Render the full HTML
    full_html = render_template_string(HTML_TEMPLATE, css=css, content=content_html)
   
    # Generate PDF
    pdf_file = BytesIO()
    pisa_status = pisa.CreatePDF(full_html, dest=pdf_file)
   
    if pisa_status.err:
        return "Error generating PDF", 500
   
    pdf_file.seek(0)
   
    return send_file(
        pdf_file,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='sql_guide.pdf'
    )
if __name__ == '__main__':
    app.run(debug=True, port=5001)