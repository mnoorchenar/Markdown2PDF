from flask import Flask, render_template_string, request, send_file
import markdown
from io import BytesIO
import re
from xhtml2pdf import pisa

app = Flask(__name__)


def extract_first_header(md_text):
    """Extract the first header from markdown text for use as filename"""
    # Match headers (# Header, ## Header, etc.)
    header_pattern = r'^#{1,6}\s+(.+?)$'
    match = re.search(header_pattern, md_text, re.MULTILINE)
    
    if match:
        header_text = match.group(1).strip()
        # Remove any markdown formatting from header (bold, italic, links, etc.)
        header_text = re.sub(r'\*\*(.+?)\*\*', r'\1', header_text)  # Bold
        header_text = re.sub(r'\*(.+?)\*', r'\1', header_text)      # Italic
        header_text = re.sub(r'__(.+?)__', r'\1', header_text)      # Bold
        header_text = re.sub(r'_(.+?)_', r'\1', header_text)        # Italic
        header_text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', header_text)  # Links
        header_text = re.sub(r'`(.+?)`', r'\1', header_text)        # Inline code
        
        # Clean up for filename (remove invalid characters)
        filename = re.sub(r'[<>:"/\\|?*]', '', header_text)
        filename = filename.strip()
        
        # Limit filename length
        if len(filename) > 100:
            filename = filename[:100].rsplit(' ', 1)[0]
        
        return filename if filename else 'document'
    
    return 'document'


def generate_css(settings):
    """Generate CSS based on user settings"""
    base_size = settings['base_font_size']
    h1_size = base_size * 2
    h2_size = base_size * 1.4
    h3_size = base_size * 1.2
    page_size = settings['page_size']
    wrap_behavior = 'pre-wrap' if settings['enable_wrap'] else 'pre'
    
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
        font-family: 'DejaVu Sans', Georgia, serif;
        line-height: 1.5;
        color: #1a1a1a;
        font-size: {settings['base_font_size']}pt;
        -pdf-encoding: utf-8;
    }}

    h1 {{
        color: #2c3e50;
        font-size: {h1_size}pt;
        margin-bottom: 15px;
        margin-top: 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #3498db;
        page-break-after: avoid;
    }}

    h2 {{
        color: #34495e;
        font-size: {h2_size}pt;
        margin-top: 20px;
        margin-bottom: 10px;
        padding-top: 5px;
        border-top: 1px solid #ecf0f1;
        page-break-after: avoid;
    }}

    h3 {{
        color: #555;
        font-size: {h3_size}pt;
        margin-top: 15px;
        margin-bottom: 8px;
        page-break-after: avoid;
    }}

    h4 {{
        color: #666;
        font-size: {base_size}pt;
        margin-top: 12px;
        margin-bottom: 6px;
    }}

    p {{
        margin-bottom: {settings['paragraph_spacing']}px;
        text-align: justify;
    }}

    strong {{
        color: #2c3e50;
        font-weight: 600;
    }}

    code {{
        font-family: 'DejaVu Sans Mono', 'DejaVu Sans', 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: {settings['base_font_size']}pt;
        color: #000000;
    }}

    pre {{
        background-color: {settings['code_bg_color']} !important;
        padding: {settings['code_padding_vertical']}px {settings['code_padding_horizontal']}px !important;
        margin: {settings['code_margin_top']}px 0 {settings['code_margin_bottom']}px 0 !important;
        border-radius: 3px;
        overflow: visible;
        word-wrap: break-word;
    }}

    pre code {{
        display: none;
    }}

    .code-line {{
        font-family: 'DejaVu Sans Mono', 'DejaVu Sans', 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: {settings['code_font_size']}pt;
        line-height: 1.4;
        margin: 0;
        padding: 0;
        border: none;
        background: transparent !important;
        display: block;
        white-space: pre-wrap;
        word-break: break-word;
    }}

    .code-block {{
        background-color: {settings['code_bg_color']} !important;
        overflow: visible;
        white-space: normal;
        word-wrap: break-word;
    }}

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
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
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
    comment_placeholder = {}
    comment_counter = 0
    
    matches = list(re.finditer(r'--[^\n]*', result))
    for match in reversed(matches):
        placeholder = f'___COMMENT_{comment_counter}___'
        comment_text = match.group(0).rstrip('\n')
        comment_placeholder[placeholder] = f'<span class="sql-comment">{comment_text}</span>'
        result = result[:match.start()] + placeholder + result[match.end():]
        comment_counter += 1
    
    matches = list(re.finditer(r'/\*.*?\*/', result, re.DOTALL))
    for match in reversed(matches):
        placeholder = f'___COMMENT_{comment_counter}___'
        comment_placeholder[placeholder] = f'<span class="sql-comment">{match.group(0)}</span>'
        result = result[:match.start()] + placeholder + result[match.end():]
        comment_counter += 1
    
    string_placeholder = {}
    string_counter = 0
    
    matches = list(re.finditer(r"'(?:[^'\\]|\\.)*'", result))
    for match in reversed(matches):
        placeholder = f'___STRING_{string_counter}___'
        string_placeholder[placeholder] = f'<span class="sql-string">{match.group(0)}</span>'
        result = result[:match.start()] + placeholder + result[match.end():]
        string_counter += 1
    
    result = re.sub(r'\b(\d+\.?\d*)\b', r'<span class="sql-number">\1</span>', result)
    
    for func in functions:
        result = re.sub(
            r'\b(' + func + r')\s*\(',
            r'<span class="sql-function">\1</span>(',
            result,
            flags=re.IGNORECASE
        )
    
    for keyword in keywords:
        result = re.sub(
            r'\b(' + keyword + r')\b',
            r'<span class="sql-keyword">\1</span>',
            result,
            flags=re.IGNORECASE
        )
    
    for placeholder, original in string_placeholder.items():
        result = result.replace(placeholder, original)
    
    for placeholder, original in comment_placeholder.items():
        result = result.replace(placeholder, original)
    
    return result


def highlight_python(code, is_pyspark=False):
    """LaTeX-quality Python/PySpark syntax highlighting"""
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
    
    # PySpark specific keywords and functions
    if is_pyspark:
        builtins.extend([
            'SparkSession', 'SparkContext', 'SQLContext', 'HiveContext',
            'DataFrame', 'Column', 'Row', 'GroupedData',
            'select', 'filter', 'where', 'groupBy', 'orderBy', 'sortBy',
            'join', 'union', 'distinct', 'drop', 'dropDuplicates',
            'withColumn', 'withColumnRenamed', 'alias', 'cast',
            'agg', 'count', 'collect', 'show', 'printSchema', 'describe',
            'read', 'write', 'csv', 'json', 'parquet', 'orc', 'jdbc',
            'createDataFrame', 'createOrReplaceTempView', 'sql',
            'cache', 'persist', 'unpersist', 'checkpoint', 'repartition', 'coalesce',
            'broadcast', 'accumulator', 'parallelize',
            'map', 'flatMap', 'reduceByKey', 'groupByKey', 'sortByKey',
            'col', 'lit', 'when', 'otherwise', 'isnull', 'isnan',
            'concat', 'concat_ws', 'substring', 'trim', 'lower', 'upper',
            'split', 'explode', 'array', 'struct', 'to_date', 'to_timestamp',
            'datediff', 'date_add', 'date_sub', 'year', 'month', 'dayofmonth',
            'window', 'partitionBy', 'over', 'rowNumber', 'rank', 'dense_rank',
            'lag', 'lead', 'first', 'last', 'collect_list', 'collect_set',
            'approx_count_distinct', 'countDistinct', 'sumDistinct',
            'udf', 'pandas_udf', 'PandasUDFType'
        ])
    
    result = code
    comment_placeholder = {}
    comment_counter = 0
    
    matches = list(re.finditer(r'#[^\n]*', result))
    for match in reversed(matches):
        placeholder = f'___COMMENT_{comment_counter}___'
        comment_text = match.group(0).rstrip('\n')
        comment_placeholder[placeholder] = f'<span class="py-comment">{comment_text}</span>'
        result = result[:match.start()] + placeholder + result[match.end():]
        comment_counter += 1
    
    string_placeholder = {}
    string_counter = 0
    
    matches = list(re.finditer(r'"""(?:[^"\\]|\\.)*?"""|\'\'\'(?:[^\'\\]|\\.)*?\'\'\'', result, re.DOTALL))
    for match in reversed(matches):
        placeholder = f'___STRING_{string_counter}___'
        string_placeholder[placeholder] = f'<span class="py-string">{match.group(0)}</span>'
        result = result[:match.start()] + placeholder + result[match.end():]
        string_counter += 1
    
    matches = list(re.finditer(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', result))
    for match in reversed(matches):
        placeholder = f'___STRING_{string_counter}___'
        string_placeholder[placeholder] = f'<span class="py-string">{match.group(0)}</span>'
        result = result[:match.start()] + placeholder + result[match.end():]
        string_counter += 1
    
    result = re.sub(r'(@\w+)', r'<span class="py-decorator">\1</span>', result)
    result = re.sub(r'\b(\d+\.?\d*)\b', r'<span class="py-number">\1</span>', result)
    
    for keyword in keywords:
        result = re.sub(r'\b(' + keyword + r')\b', r'<span class="py-keyword">\1</span>', result)
    
    for builtin in builtins:
        result = re.sub(r'\b(' + builtin + r')\b', r'<span class="py-builtin">\1</span>', result)
    
    for placeholder, original in string_placeholder.items():
        result = result.replace(placeholder, original)
    
    for placeholder, original in comment_placeholder.items():
        result = result.replace(placeholder, original)
    
    return result


def highlight_r(code):
    """LaTeX-quality R syntax highlighting"""
    keywords = [
        'if', 'else', 'for', 'while', 'repeat', 'in', 'next', 'break',
        'function', 'return', 'TRUE', 'FALSE', 'NULL', 'NA', 'NA_integer_',
        'NA_real_', 'NA_complex_', 'NA_character_', 'Inf', 'NaN',
        'library', 'require', 'source', 'setwd', 'getwd'
    ]
    builtins = [
        'print', 'cat', 'paste', 'paste0', 'sprintf', 'format',
        'c', 'list', 'vector', 'matrix', 'array', 'data.frame', 'tibble',
        'length', 'nrow', 'ncol', 'dim', 'names', 'colnames', 'rownames',
        'head', 'tail', 'str', 'summary', 'class', 'typeof', 'mode',
        'sum', 'mean', 'median', 'sd', 'var', 'min', 'max', 'range',
        'abs', 'sqrt', 'log', 'log10', 'log2', 'exp', 'round', 'floor', 'ceiling',
        'seq', 'rep', 'sort', 'order', 'rank', 'rev', 'unique', 'duplicated',
        'which', 'any', 'all', 'is.na', 'is.null', 'is.numeric', 'is.character',
        'as.numeric', 'as.character', 'as.factor', 'as.Date', 'as.POSIXct',
        'subset', 'merge', 'rbind', 'cbind', 'split', 'apply', 'lapply', 'sapply',
        'mapply', 'tapply', 'aggregate', 'transform', 'within',
        'read.csv', 'read.table', 'write.csv', 'write.table', 'readRDS', 'saveRDS',
        'grep', 'grepl', 'sub', 'gsub', 'regexpr', 'strsplit', 'nchar', 'substr',
        'tolower', 'toupper', 'trimws', 'chartr',
        'factor', 'levels', 'nlevels', 'droplevels', 'cut', 'table', 'prop.table',
        'plot', 'hist', 'boxplot', 'barplot', 'pie', 'lines', 'points', 'abline',
        'ggplot', 'aes', 'geom_point', 'geom_line', 'geom_bar', 'geom_histogram',
        'geom_boxplot', 'facet_wrap', 'facet_grid', 'theme', 'labs', 'ggtitle',
        'mutate', 'select', 'filter', 'arrange', 'group_by', 'summarise', 'summarize',
        'left_join', 'right_join', 'inner_join', 'full_join', 'anti_join', 'semi_join',
        'bind_rows', 'bind_cols', 'pivot_longer', 'pivot_wider', 'gather', 'spread',
        'rename', 'relocate', 'across', 'everything', 'starts_with', 'ends_with',
        'contains', 'matches', 'num_range', 'where', 'pull', 'distinct', 'count',
        'slice', 'slice_head', 'slice_tail', 'slice_min', 'slice_max', 'slice_sample',
        'lm', 'glm', 'aov', 'anova', 't.test', 'chisq.test', 'cor', 'cov',
        'predict', 'fitted', 'residuals', 'coef', 'confint',
        'tryCatch', 'stop', 'warning', 'message', 'stopifnot'
    ]
    
    result = code
    comment_placeholder = {}
    comment_counter = 0
    
    # R comments start with #
    matches = list(re.finditer(r'#[^\n]*', result))
    for match in reversed(matches):
        placeholder = f'___COMMENT_{comment_counter}___'
        comment_text = match.group(0).rstrip('\n')
        comment_placeholder[placeholder] = f'<span class="py-comment">{comment_text}</span>'
        result = result[:match.start()] + placeholder + result[match.end():]
        comment_counter += 1
    
    string_placeholder = {}
    string_counter = 0
    
    # Double and single quoted strings
    matches = list(re.finditer(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', result))
    for match in reversed(matches):
        placeholder = f'___STRING_{string_counter}___'
        string_placeholder[placeholder] = f'<span class="py-string">{match.group(0)}</span>'
        result = result[:match.start()] + placeholder + result[match.end():]
        string_counter += 1
    
    # Highlight numbers (including scientific notation)
    result = re.sub(r'\b(\d+\.?\d*(?:[eE][+-]?\d+)?[Li]?)\b', r'<span class="py-number">\1</span>', result)
    
    # Highlight keywords
    for keyword in keywords:
        result = re.sub(r'\b(' + re.escape(keyword) + r')\b', r'<span class="py-keyword">\1</span>', result)
    
    # Highlight builtins/functions
    for builtin in builtins:
        result = re.sub(r'\b(' + re.escape(builtin) + r')\b', r'<span class="py-builtin">\1</span>', result)
    
    # Highlight assignment operators
    result = re.sub(r'(&lt;-|&lt;&lt;-|-&gt;|-&gt;&gt;)', r'<span class="py-keyword">\1</span>', result)
    result = re.sub(r'(<-|<<-|->|->>)', r'<span class="py-keyword">\1</span>', result)
    
    # Highlight pipe operators
    result = re.sub(r'(%&gt;%|%&lt;&gt;%|\|&gt;)', r'<span class="sql-function">\1</span>', result)
    result = re.sub(r'(%>%|%<>%|\|>)', r'<span class="sql-function">\1</span>', result)
    
    # Restore strings and comments
    for placeholder, original in string_placeholder.items():
        result = result.replace(placeholder, original)
    
    for placeholder, original in comment_placeholder.items():
        result = result.replace(placeholder, original)
    
    return result


def process_code_blocks(md_text, enable_wrap=True):
    """Process all code blocks in markdown"""
    
    def replace_code_block(match):
        lang = match.group(1) if match.group(1) else ''
        code = match.group(2).strip('\n')
        lang_lower = lang.lower().strip()
        
        code = code.replace('├──', '|--')
        code = code.replace('└──', '`--')
        code = code.replace('├─', '|-')
        code = code.replace('└─', '`-')
        code = code.replace('│', '|')
        code = code.replace('─', '-')
        code = code.replace('├', '|')
        code = code.replace('└', '`')
        
        if lang_lower in ['sql', 'mysql', 'postgresql', 'postgres', 'sqlite', 'tsql', 'plsql']:
            highlighted = highlight_sql(code)
        elif lang_lower in ['python', 'py', 'python3']:
            highlighted = highlight_python(code, is_pyspark=False)
        elif lang_lower in ['pyspark', 'spark']:
            highlighted = highlight_python(code, is_pyspark=True)
        elif lang_lower in ['r', 'rlang', 'rscript']:
            highlighted = highlight_r(code)
        else:
            highlighted = code
        
        lines = highlighted.split('\n')
        html_lines = ''.join(f'<div class="code-line">{line if line.strip() else " "}</div>' for line in lines)
        return f'<pre class="code-block">{html_lines}</pre>'
    
    result = re.sub(r'```([a-zA-Z0-9]*)\n(.*?)\n```', replace_code_block, md_text, flags=re.DOTALL)
    result = re.sub(r'```([a-zA-Z0-9]*)\n(.*?)```', replace_code_block, result, flags=re.DOTALL)
    result = re.sub(r'```\s*([a-zA-Z0-9]*)\s*\n(.*?)```', replace_code_block, result, flags=re.DOTALL)
    
    return result


def process_markdown(md_text, enable_wrap=True):
    """Convert markdown to HTML with syntax highlighting"""
    md_with_highlighted_code = process_code_blocks(md_text, enable_wrap)
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
        .field select {
            width: 100%;
            padding: 8px;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            font-size: 0.9em;
        }
        .field input:focus, .field select:focus {
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
        .wrap-toggle {
            background-color: #e7f3ff;
            padding: 12px;
            border-radius: 8px;
            border-left: 3px solid #667eea;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 Markdown to PDF Converter</h1>
        <p class="subtitle">PDF filename will be based on your first header</p>
        
        <form method="POST" action="/generate">
            <div class="main-grid">
                <div class="textarea-wrapper">
                    <textarea name="markdown" placeholder="# Your Document Title

Your content here...

```sql
SELECT * FROM users;
```"></textarea>
                    <button type="submit" class="btn-generate">Generate PDF</button>
                </div>
                
                <div class="settings-panel">
                    <h3>⚙️ PDF Settings</h3>
                    
                    <div class="preset-grid">
                        <button type="button" class="btn-preset" onclick="applyDefault()">Default</button>
                        <button type="button" class="btn-preset compact" onclick="applyCompact()">Compact</button>
                    </div>

                    <div class="wrap-toggle">
                        <div class="checkbox-field">
                            <input type="checkbox" name="enable_wrap" id="enable_wrap" value="true" checked>
                            <label for="enable_wrap">✨ Enable code wrapping</label>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h4>📝 Font Sizes</h4>
                        <div class="field">
                            <label>Text Size (pt)</label>
                            <input type="number" name="base_font_size" value="12" step="0.5" min="7" max="14">
                        </div>
                        <div class="field">
                            <label>Code Size (pt)</label>
                            <input type="number" name="code_font_size" value="11" step="0.5" min="6" max="12">
                        </div>
                    </div>
                    
                    <div class="section">
                        <h4>📄 Page Settings</h4>
                        <div class="field">
                            <label>Page Size</label>
                            <select name="page_size">
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
                    
                    <div class="section">
                        <h4>📦 Code Box Style</h4>
                        <div class="field">
                            <label>Background Color</label>
                            <input type="color" name="code_bg_color" value="#f5f5f5">
                        </div>
                    </div>
                    
                    <div class="section">
                        <h4>🎨 Syntax Highlighting</h4>
                        <div class="field">
                            <label>Keywords</label>
                            <input type="color" name="keyword_color" value="#00BFFF">
                        </div>
                        <div class="field">
                            <label>Strings</label>
                            <input type="color" name="string_color" value="#ff8c00">
                        </div>
                        <div class="field">
                            <label>Comments</label>
                            <input type="color" name="comment_color" value="#006400">
                        </div>
                        <div class="field">
                            <label>Numbers</label>
                            <input type="color" name="number_color" value="#FF00FF">
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
            document.querySelector('[name="base_font_size"]').value = 12;
            document.querySelector('[name="code_font_size"]').value = 11;
            document.querySelector('[name="page_size"]').value = "A4";
            document.querySelector('[name="page_margin"]').value = 1.5;
            document.querySelector('[name="paragraph_spacing"]').value = 8;
            document.querySelector('[name="code_padding_vertical"]').value = 15;
            document.querySelector('[name="code_padding_horizontal"]').value = 12;
            document.querySelector('[name="code_margin_top"]').value = 15;
            document.querySelector('[name="code_margin_bottom"]').value = 15;
            document.querySelector('[name="code_bg_color"]').value = "#f5f5f5";
            document.querySelector('[name="keyword_color"]').value = "#00BFFF";
            document.querySelector('[name="string_color"]').value = "#ff8c00";
            document.querySelector('[name="comment_color"]').value = "#006400";
            document.querySelector('[name="number_color"]').value = "#FF00FF";
            document.querySelector('[name="function_color"]').value = "#795e26";
            document.querySelector('#enable_wrap').checked = true;
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
            document.querySelector('[name="code_bg_color"]').value = "#f5f5f5";
            document.querySelector('[name="keyword_color"]').value = "#0000ff";
            document.querySelector('[name="string_color"]').value = "#ff8c00";
            document.querySelector('[name="comment_color"]').value = "#006400";
            document.querySelector('[name="number_color"]').value = "#098658";
            document.querySelector('[name="function_color"]').value = "#795e26";
            document.querySelector('#enable_wrap').checked = true;
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
    
    # Extract filename from first header
    pdf_filename = extract_first_header(markdown_text) + '.pdf'
    
    settings = {
        'base_font_size': float(request.form.get('base_font_size', 12)),
        'code_font_size': float(request.form.get('code_font_size', 11)),
        'page_size': request.form.get('page_size', 'A4'),
        'page_margin': float(request.form.get('page_margin', 1.5)),
        'paragraph_spacing': int(request.form.get('paragraph_spacing', 8)),
        'code_padding_vertical': int(request.form.get('code_padding_vertical', 15)),
        'code_padding_horizontal': int(request.form.get('code_padding_horizontal', 12)),
        'code_margin_top': int(request.form.get('code_margin_top', 15)),
        'code_margin_bottom': int(request.form.get('code_margin_bottom', 15)),
        'code_bg_color': request.form.get('code_bg_color', '#f5f5f5'),
        'keyword_color': request.form.get('keyword_color', '#00BFFF'),
        'string_color': request.form.get('string_color', '#ff8c00'),
        'comment_color': request.form.get('comment_color', '#006400'),
        'number_color': request.form.get('number_color', '#FF00FF'),
        'function_color': request.form.get('function_color', '#795e26'),
        'enable_wrap': request.form.get('enable_wrap') == 'true',
    }
    
    css = generate_css(settings)
    content_html = process_markdown(markdown_text, settings['enable_wrap'])
    full_html = render_template_string(HTML_TEMPLATE, css=css, content=content_html)
    
    pdf_file = BytesIO()
    pisa_status = pisa.CreatePDF(
        full_html.encode('utf-8'),
        dest=pdf_file,
        encoding='utf-8',
        path=''
    )
    
    if pisa_status.err:
        return "Error generating PDF", 500
    
    pdf_file.seek(0)
    
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