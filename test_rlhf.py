import asyncio
from app.services.quickml import quickml_generate
from app.core.antar_identity import system_prompt

async def main():
    q = 'What are the overall crime patterns in Karnataka across all zones?'
    print('Testing query:', q)
    prompt = system_prompt('synthesis')
    print('\n--- System Prompt ---')
    print(prompt)
    print('---------------------\n')
    
    # We simulate what the LLM synthesis would do
    res = await quickml_generate(system=prompt, user=f'Original Query: {q}\nContext Data: (Simulated tabular data)', max_tokens=300)
    print('\n--- LLM Response ---')
    print(res)

if __name__ == '__main__':
    asyncio.run(main())

