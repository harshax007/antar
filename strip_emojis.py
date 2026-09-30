import os
import re

# Regex to match emojis
# Ranges cover standard emojis and symbols
emoji_pattern = re.compile(
    u"([\\U00010000-\\U0010ffff]|[\\u2600-\\u27BF])",
    re.UNICODE
)

def remove_emojis(directory):
    for root, dirs, files in os.walk(directory):
        if 'node_modules' in dirs:
            dirs.remove('node_modules')
        if '.next' in dirs:
            dirs.remove('.next')
        for file in files:
            if file.endswith(('.jsx', '.js', '.tsx', '.ts')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Remove emojis
                    new_content = emoji_pattern.sub(r'', content)
                    
                    if content != new_content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Removed emojis from {filepath}")
                except Exception as e:
                    pass

remove_emojis('D:\\Project\\antar-frontend')
