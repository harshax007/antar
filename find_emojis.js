const fs = require('fs');
const path = require('path');
const emojiRegex = require('emoji-regex');

const regex = emojiRegex();

function walk(dir) {
    let results = [];
    const list = fs.readdirSync(dir);
    list.forEach(file => {
        if (file === 'node_modules' || file === '.next') return;
        file = path.resolve(dir, file);
        const stat = fs.statSync(file);
        if (stat && stat.isDirectory()) {
            results = results.concat(walk(file));
        } else if (file.endsWith('.js') || file.endsWith('.jsx') || file.endsWith('.tsx') || file.endsWith('.ts')) {
            const content = fs.readFileSync(file, 'utf8');
            const match = content.match(regex);
            if (match) {
                results.push({ file, emojis: [...new Set(match)] });
            }
        }
    });
    return results;
}

const found = walk('D:\\Project\\antar-frontend');
found.forEach(f => console.log(f.file, f.emojis));
