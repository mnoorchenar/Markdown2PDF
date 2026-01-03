import subprocess
import tempfile
import os
import re
from io import BytesIO
from flask import Flask, render_template_string, request, send_file

app = Flask(__name__)


def extract_first_header(md_text):
    """Extract the first header from markdown text for use as filename."""
    header_pattern = r'^#{1,6}\s+(.+?)$'
    match = re.search(header_pattern, md_text, re.MULTILINE)
    
    if match:
        header_text = match.group(1).strip()
        header_text = re.sub(r'\*\*(.+?)\*\*', r'\1', header_text)
        header_text = re.sub(r'\*(.+?)\*', r'\1', header_text)
        header_text = re.sub(r'__(.+?)__', r'\1', header_text)
        header_text = re.sub(r'_(.+?)_', r'\1', header_text)
        header_text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', header_text)
        header_text = re.sub(r'`(.+?)`', r'\1', header_text)
        filename = re.sub(r'[<>:"/\\|?*]', '', header_text)
        filename = filename.strip()
        
        if len(filename) > 100:
            filename = filename[:100].rsplit(' ', 1)[0]
        
        return filename if filename else 'document'
    
    return 'document'


def remove_emojis(content):
    """Remove all emojis from content."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U00002600-\U000026FF"
        "\U00002700-\U000027BF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002B50"
        "\U0000FE0F"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', content)


def create_latex_header(settings):
    """Create LaTeX header with listings configuration based on settings."""
    header = rf"""
\usepackage{{listings}}
\usepackage{{xcolor}}
\usepackage{{fontspec}}

% Define colors from settings
\definecolor{{codebg}}{{HTML}}{{{settings['code_bg_color'].lstrip('#')}}}
\definecolor{{keywordcolor}}{{HTML}}{{{settings['keyword_color'].lstrip('#')}}}
\definecolor{{stringcolor}}{{HTML}}{{{settings['string_color'].lstrip('#')}}}
\definecolor{{commentcolor}}{{HTML}}{{{settings['comment_color'].lstrip('#')}}}
\definecolor{{numbercolor}}{{HTML}}{{{settings['number_color'].lstrip('#')}}}
\definecolor{{functioncolor}}{{HTML}}{{{settings['function_color'].lstrip('#')}}}

% Define Python style
\lstdefinestyle{{pythonstyle}}{{
    language=Python,
    backgroundcolor=\color{{codebg}},
    basicstyle=\fontsize{{{settings['code_font_size']}}}{{{settings['code_font_size'] + 2}}}\selectfont\ttfamily,
    keywordstyle=\color{{keywordcolor}}\bfseries,
    commentstyle=\color{{commentcolor}}\itshape,
    stringstyle=\color{{stringcolor}},
    numberstyle=\tiny\color{{gray}},
    numbers=none,
    breaklines=true,
    showstringspaces=false,
    tabsize=4,
    frame=single,
    framesep=5pt,
    xleftmargin={settings['code_padding_horizontal']}pt,
    xrightmargin={settings['code_padding_horizontal']}pt,
    aboveskip={settings['code_margin_top']}pt,
    belowskip={settings['code_margin_bottom']}pt,
    morekeywords={{self, True, False, None, as, with, yield, async, await}}
}}

% Define SQL style
\lstdefinestyle{{sqlstyle}}{{
    language=SQL,
    backgroundcolor=\color{{codebg}},
    basicstyle=\fontsize{{{settings['code_font_size']}}}{{{settings['code_font_size'] + 2}}}\selectfont\ttfamily,
    keywordstyle=\color{{keywordcolor}}\bfseries,
    commentstyle=\color{{commentcolor}}\itshape,
    stringstyle=\color{{stringcolor}},
    numberstyle=\tiny\color{{gray}},
    numbers=none,
    breaklines=true,
    showstringspaces=false,
    tabsize=4,
    frame=single,
    framesep=5pt,
    xleftmargin={settings['code_padding_horizontal']}pt,
    xrightmargin={settings['code_padding_horizontal']}pt,
    aboveskip={settings['code_margin_top']}pt,
    belowskip={settings['code_margin_bottom']}pt,
    morekeywords={{LIMIT, OFFSET, BOOLEAN, JSON, ARRAY, SERIAL}}
}}

% Define R style
\lstdefinestyle{{rstyle}}{{
    language=R,
    backgroundcolor=\color{{codebg}},
    basicstyle=\fontsize{{{settings['code_font_size']}}}{{{settings['code_font_size'] + 2}}}\selectfont\ttfamily,
    keywordstyle=\color{{keywordcolor}}\bfseries,
    commentstyle=\color{{commentcolor}}\itshape,
    stringstyle=\color{{stringcolor}},
    numberstyle=\tiny\color{{gray}},
    numbers=none,
    breaklines=true,
    showstringspaces=false,
    tabsize=4,
    frame=single,
    framesep=5pt,
    xleftmargin={settings['code_padding_horizontal']}pt,
    xrightmargin={settings['code_padding_horizontal']}pt,
    aboveskip={settings['code_margin_top']}pt,
    belowskip={settings['code_margin_bottom']}pt,
    morekeywords={{TRUE, FALSE, NULL, NA, library, require, function}}
}}

% Default style
\lstdefinestyle{{defaultstyle}}{{
    backgroundcolor=\color{{codebg}},
    basicstyle=\fontsize{{{settings['code_font_size']}}}{{{settings['code_font_size'] + 2}}}\selectfont\ttfamily,
    breaklines=true,
    showstringspaces=false,
    tabsize=4,
    frame=single,
    framesep=5pt,
    xleftmargin={settings['code_padding_horizontal']}pt,
    xrightmargin={settings['code_padding_horizontal']}pt,
    aboveskip={settings['code_margin_top']}pt,
    belowskip={settings['code_margin_bottom']}pt
}}

\lstset{{style=defaultstyle}}
"""
    return header


def get_language_style(lang):
    """Map language identifier to LaTeX listing style."""
    if not lang:
        return 'defaultstyle'
    
    lang = lang.lower().strip()
    
    if lang in ['python', 'py', 'python3', 'pyspark', 'spark']:
        return 'pythonstyle'
    elif lang in ['sql', 'mysql', 'postgresql', 'postgres', 'sqlite', 'tsql', 'plsql']:
        return 'sqlstyle'
    elif lang in ['r', 'rlang', 'rscript']:
        return 'rstyle'
    
    return 'defaultstyle'


def clean_special_chars(code):
    """Replace special unicode characters with ASCII equivalents."""
    replacements = [
        ('├──', '|--'),
        ('└──', '`--'),
        ('├─', '|-'),
        ('└─', '`-'),
        ('│', '|'),
        ('─', '-'),
        ('├', '|'),
        ('└', '`'),
    ]
    for old, new in replacements:
        code = code.replace(old, new)
    return code


def process_code_blocks(content):
    """Convert markdown code blocks to LaTeX listings."""
    
    def replace_code_block(match):
        lang = match.group(1) if match.group(1) else ''
        code = match.group(2)
        
        lang_style = get_language_style(lang)
        code = clean_special_chars(code)
        
        code = code.strip('\n')
        
        return f'''
```{{=latex}}
\\begin{{lstlisting}}[style={lang_style}]
{code}
\\end{{lstlisting}}
```
'''
    
    pattern = r'```(\w*)\n(.*?)```'
    result = re.sub(pattern, replace_code_block, content, flags=re.DOTALL)
    
    return result


def preprocess_markdown(md_text):
    """Preprocess markdown for Pandoc conversion."""
    content = remove_emojis(md_text)
    content = process_code_blocks(content)
    return content


def convert_md_to_pdf(md_text, settings):
    """Convert markdown to PDF using Pandoc with XeLaTeX."""
    processed_content = preprocess_markdown(md_text)
    
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.tex', delete=False, encoding='utf-8'
    ) as header_file:
        header_file.write(create_latex_header(settings))
        header_path = header_file.name
    
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.md', delete=False, encoding='utf-8'
    ) as temp_md:
        temp_md.write(processed_content)
        temp_md_path = temp_md.name
    
    with tempfile.NamedTemporaryFile(
        suffix='.pdf', delete=False
    ) as temp_pdf:
        output_path = temp_pdf.name
    
    page_size_map = {
        'A4': 'a4paper',
        'Letter': 'letterpaper',
        'Legal': 'legalpaper',
        'A3': 'a3paper'
    }
    paper = page_size_map.get(settings['page_size'], 'a4paper')
    
    cmd = [
        'pandoc',
        temp_md_path,
        '-o', output_path,
        '--pdf-engine=xelatex',
        '-H', header_path,
        '-V', f'geometry:margin={settings["page_margin"]}cm',
        '-V', f'fontsize={settings["base_font_size"]}pt',
        '-V', f'geometry:{paper}',
        '-V', f'parskip={settings["paragraph_spacing"]}pt',
        '--highlight-style=tango'
    ]
    
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
        
        with open(output_path, 'rb') as f:
            pdf_content = f.read()
        
        return pdf_content, None
        
    except subprocess.CalledProcessError as e:
        return None, f"Pandoc error: {e.stderr}"
    except FileNotFoundError:
        return None, "Pandoc not found. Please install pandoc and xelatex."
    finally:
        for path in [header_path, temp_md_path, output_path]:
            if os.path.exists(path):
                os.unlink(path)


@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Markdown to PDF Converter (Pandoc)</title>
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
        h1 { color: #2c3e50; margin-bottom: 5px; font-size: 2em; }
        .subtitle { color: #7f8c8d; margin-bottom: 15px; font-size: 1em; }
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
        textarea:focus { outline: none; border-color: #667eea; }
        .settings-panel {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            overflow-y: auto;
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
        .section:last-child { border-bottom: none; margin-bottom: 0; }
        .section h4 {
            color: #495057;
            font-size: 0.95em;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .field { margin-bottom: 12px; }
        .field label {
            display: block;
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
            font-weight: 500;
        }
        .field input[type="number"], .field select {
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
        .field input:focus, .field select:focus {
            outline: none;
            border-color: #667eea;
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
        .btn-preset:hover { background: #28a745; color: white; }
        .btn-preset.compact { border-color: #17a2b8; color: #17a2b8; }
        .btn-preset.compact:hover { background: #17a2b8; }
        form {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            min-height: 0;
        }
        .info-box {
            background-color: #e7f3ff;
            padding: 12px;
            border-radius: 8px;
            border-left: 3px solid #667eea;
            margin-bottom: 15px;
            font-size: 0.85em;
            color: #495057;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Markdown to PDF Converter</h1>
        <p class="subtitle">Powered by Pandoc + XeLaTeX</p>
        
        <form method="POST" action="/generate">
            <div class="main-grid">
                <div class="textarea-wrapper">
                    <textarea name="markdown" placeholder="# Your Document Title

Your content here...

```python
def hello():
    print('Hello, World!')
```

```sql
SELECT * FROM users WHERE active = TRUE;
```"></textarea>
                    <button type="submit" class="btn-generate">Generate PDF</button>
                </div>
                
                <div class="settings-panel">
                    <h3>PDF Settings</h3>
                    
                    <div class="info-box">
                        Uses Pandoc with XeLaTeX for professional typography and syntax highlighting.
                    </div>
                    
                    <div class="preset-grid">
                        <button type="button" class="btn-preset" onclick="applyDefault()">Default</button>
                        <button type="button" class="btn-preset compact" onclick="applyCompact()">Compact</button>
                    </div>
                    
                    <div class="section">
                        <h4>Font Sizes</h4>
                        <div class="field">
                            <label>Text Size (pt)</label>
                            <input type="number" name="base_font_size" value="11" step="1" min="8" max="14">
                        </div>
                        <div class="field">
                            <label>Code Size (pt)</label>
                            <input type="number" name="code_font_size" value="9" step="1" min="6" max="12">
                        </div>
                    </div>
                    
                    <div class="section">
                        <h4>Page Settings</h4>
                        <div class="field">
                            <label>Page Size</label>
                            <select name="page_size">
                                <option value="A4">A4</option>
                                <option value="Letter">Letter</option>
                                <option value="Legal">Legal</option>
                                <option value="A3">A3</option>
                            </select>
                        </div>
                        <div class="field">
                            <label>Page Margin (cm)</label>
                            <input type="number" name="page_margin" value="2" step="0.1" min="0.5" max="4">
                        </div>
                    </div>
                    
                    <div class="section">
                        <h4>Spacing</h4>
                        <div class="field">
                            <label>Paragraph Spacing (pt)</label>
                            <input type="number" name="paragraph_spacing" value="6" step="1" min="0" max="20">
                        </div>
                        <div class="field">
                            <label>Code Padding (pt)</label>
                            <input type="number" name="code_padding_horizontal" value="15" step="1" min="5" max="30">
                        </div>
                        <div class="field">
                            <label>Code Margin Top (pt)</label>
                            <input type="number" name="code_margin_top" value="10" step="1" min="0" max="30">
                        </div>
                        <div class="field">
                            <label>Code Margin Bottom (pt)</label>
                            <input type="number" name="code_margin_bottom" value="10" step="1" min="0" max="30">
                        </div>
                    </div>
                    
                    <div class="section">
                        <h4>Code Box Style</h4>
                        <div class="field">
                            <label>Background Color</label>
                            <input type="color" name="code_bg_color" value="#f5f5f5">
                        </div>
                    </div>
                    
                    <div class="section">
                        <h4>Syntax Highlighting</h4>
                        <div class="field">
                            <label>Keywords</label>
                            <input type="color" name="keyword_color" value="#0000ff">
                        </div>
                        <div class="field">
                            <label>Strings</label>
                            <input type="color" name="string_color" value="#a31515">
                        </div>
                        <div class="field">
                            <label>Comments</label>
                            <input type="color" name="comment_color" value="#008000">
                        </div>
                        <div class="field">
                            <label>Numbers</label>
                            <input type="color" name="number_color" value="#098658">
                        </div>
                        <div class="field">
                            <label>Functions</label>
                            <input type="color" name="function_color" value="#795e26">
                        </div>
                    </div>
                </div>
            </div>
        </form>
    </div>
    
    <script>
        function applyDefault() {
            document.querySelector('[name="base_font_size"]').value = 11;
            document.querySelector('[name="code_font_size"]').value = 9;
            document.querySelector('[name="page_size"]').value = "A4";
            document.querySelector('[name="page_margin"]').value = 2;
            document.querySelector('[name="paragraph_spacing"]').value = 6;
            document.querySelector('[name="code_padding_horizontal"]').value = 15;
            document.querySelector('[name="code_margin_top"]').value = 10;
            document.querySelector('[name="code_margin_bottom"]').value = 10;
            document.querySelector('[name="code_bg_color"]').value = "#f5f5f5";
            document.querySelector('[name="keyword_color"]').value = "#0000ff";
            document.querySelector('[name="string_color"]').value = "#a31515";
            document.querySelector('[name="comment_color"]').value = "#008000";
            document.querySelector('[name="number_color"]').value = "#098658";
            document.querySelector('[name="function_color"]').value = "#795e26";
        }
        
        function applyCompact() {
            document.querySelector('[name="base_font_size"]').value = 10;
            document.querySelector('[name="code_font_size"]').value = 8;
            document.querySelector('[name="page_size"]').value = "A4";
            document.querySelector('[name="page_margin"]').value = 1.5;
            document.querySelector('[name="paragraph_spacing"]').value = 4;
            document.querySelector('[name="code_padding_horizontal"]').value = 10;
            document.querySelector('[name="code_margin_top"]').value = 6;
            document.querySelector('[name="code_margin_bottom"]').value = 6;
            document.querySelector('[name="code_bg_color"]').value = "#f8f8f8";
            document.querySelector('[name="keyword_color"]').value = "#0000ff";
            document.querySelector('[name="string_color"]').value = "#a31515";
            document.querySelector('[name="comment_color"]').value = "#008000";
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
    
    pdf_filename = extract_first_header(markdown_text) + '.pdf'
    
    settings = {
        'base_font_size': int(request.form.get('base_font_size', 11)),
        'code_font_size': int(request.form.get('code_font_size', 9)),
        'page_size': request.form.get('page_size', 'A4'),
        'page_margin': float(request.form.get('page_margin', 2)),
        'paragraph_spacing': int(request.form.get('paragraph_spacing', 6)),
        'code_padding_horizontal': int(request.form.get('code_padding_horizontal', 15)),
        'code_margin_top': int(request.form.get('code_margin_top', 10)),
        'code_margin_bottom': int(request.form.get('code_margin_bottom', 10)),
        'code_bg_color': request.form.get('code_bg_color', '#f5f5f5'),
        'keyword_color': request.form.get('keyword_color', '#0000ff'),
        'string_color': request.form.get('string_color', '#a31515'),
        'comment_color': request.form.get('comment_color', '#008000'),
        'number_color': request.form.get('number_color', '#098658'),
        'function_color': request.form.get('function_color', '#795e26'),
    }
    
    pdf_content, error = convert_md_to_pdf(markdown_text, settings)
    
    if error:
        return f"Error generating PDF: {error}", 500
    
    pdf_file = BytesIO(pdf_content)
    
    return send_file(
        pdf_file,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=pdf_filename
    )


def main():
    app.run(debug=True, port=5001)


if __name__ == '__main__':
    main()