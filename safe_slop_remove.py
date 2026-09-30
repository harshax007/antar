import os
import re

# Emojis and slop
emoji_pattern = re.compile(u"([\\U00010000-\\U0010ffff]|[\\u2600-\\u27BF])", re.UNICODE)
slop_patterns = [
    (re.compile(r'Revolutionize your workflow', re.IGNORECASE), ''),
    (re.compile(r'Unlock the power of', re.IGNORECASE), ''),
    (re.compile(r' — '), ' - '),
    (re.compile(r' -- '), ' - '),
]
css_slop = [
    (re.compile(r'#8B5CF6', re.IGNORECASE), '#475569'), # Slate 700
    (re.compile(r'rgba\(139,\s*92,\s*246,\s*0?\.\d+\)', re.IGNORECASE), 'rgba(255,255,255,0.05)'),
]

def clean_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        new_content = emoji_pattern.sub(r'', content)
        for pattern, repl in slop_patterns:
            new_content = pattern.sub(repl, new_content)
            
        if filepath.endswith('.css'):
            for pattern, repl in css_slop:
                new_content = pattern.sub(repl, new_content)
                
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Cleaned {filepath}")
    except Exception as e:
        pass

def walk_dir(directory):
    for root, dirs, files in os.walk(directory):
        if 'node_modules' in dirs: dirs.remove('node_modules')
        if '.next' in dirs: dirs.remove('.next')
        for file in files:
            if file.endswith(('.jsx', '.js', '.tsx', '.ts', '.css')):
                clean_file(os.path.join(root, file))

walk_dir('D:\\Project\\antar-frontend')
