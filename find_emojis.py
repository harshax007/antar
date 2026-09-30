import os
import re

def find_emojis(directory):
    for root, dirs, files in os.walk(directory):
        if 'node_modules' in dirs:
            dirs.remove('node_modules')
        if '.next' in dirs:
            dirs.remove('.next')
        for file in files:
            if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Find characters outside ASCII and Kannada ranges
                        # Emojis are usually in 1F300-1F9FF, 2600-26FF, 2700-27BF, etc.
                        emojis = set(re.findall(r'[\U00010000-\U0010ffff]', content))
                        if emojis:
                            print(f"{filepath} has: {''.join(emojis)}")
                except Exception as e:
                    pass

find_emojis('D:\\Project\\antar-frontend')
