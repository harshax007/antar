import sys

filepath = r"D:\Project\antar-frontend\components\BrainStructure.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Add CustomDropdown component at the top, just after imports
dropdown_code = """
function CustomDropdown({ value, options, onChange, label, ariaLabel }) {
  const [open, setOpen] = useState(false);
  const selected = options.find(o => o.value === value) || options[0];
  return (
    <div className="custom-dropdown" style={{position: 'relative', display: 'inline-block'}}>
      <button 
        type="button"
        className="bsx-sel" 
        style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', cursor: 'pointer', background: '#0a1526', border: '1px solid #1a3a5a', padding: '6px 12px', borderRadius: '4px', color: '#cfe9ee'}}
        onClick={() => setOpen(!open)}
        aria-label={ariaLabel}
      >
        <span>{selected.label}</span>
        <svg width="10" height="6" viewBox="0 0 10 6" fill="none"><path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
      </button>
      {open && (
        <div className="custom-dropdown-menu" style={{position: 'absolute', top: '100%', left: 0, zIndex: 100, background: '#0a1526', border: '1px solid #1a3a5a', borderRadius: '4px', marginTop: '4px', minWidth: '100%', maxHeight: '300px', overflowY: 'auto'}}>
          {options.map((o) => (
            <div 
              key={o.value} 
              style={{padding: '6px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap'}}
              onClick={() => { onChange(o.value); setOpen(false); }}
              onMouseOver={(e) => e.currentTarget.style.background = '#122b46'}
              onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
            >
              {o.color && <div style={{width: '8px', height: '8px', borderRadius: '50%', background: o.color}}></div>}
              {o.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
"""

if "function CustomDropdown" not in content:
    content = content.replace('const API =', dropdown_code + '\nconst API =')

# Replace <select> with CustomDropdown in BrainStructure.jsx
# It's a bit complex with regex, let's just write a python logic to replace the blocks

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Added CustomDropdown")
