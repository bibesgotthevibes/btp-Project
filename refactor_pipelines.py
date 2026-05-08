import sys
import re

def refactor_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # 1. Guard the pip install block
    content = content.replace('print("Step 0: Installing required libraries ...")', 
        'if __name__ == "__main__":\n    print("Step 0: Installing required libraries ...")')
    
    content = re.sub(r'(\n_pip\(.*?\)\nprint\(.*?"\)\n)', r'\n    \1', content)
    content = content.replace('_pip("openpyxl"', '    _pip("openpyxl"')
    content = content.replace('print("  [1', '    print("  [1')
    content = content.replace('_pip("--no-deps"', '    _pip("--no-deps"')
    content = content.replace('print("  [2', '    print("  [2')
    content = content.replace('print("  [3', '    print("  [3')
    content = content.replace('print("  ✓ All', '    print("  ✓ All')

    # Find the end of imports and function definitions.
    # The first line that triggers global dataframe loading is often around STEP 2 or STEP 3 depending    # The first line that trll just ma    #  search for stan    # The first line that tha    # The first line that triggeratement = 'print("\\nApplying     # The first line thattement not i    # The first line that triggers global dataframe loading is often around STEP atem    # The first line that triggers global dataframe loading is ofte len(parts) == 2:
            #             #             #             #             #             #                       #             #             #             #                             #             #             #             #     _bot            #             #             #             #             #  ttom_half.split("\n")])
            
            content = top_half            content = top_half            content = top_half th open(filepath, 'w') as f:
        f.write(content)

for p in ["SciFive/scifive_pipeline.py", "BioBART/biobart_lay_english_pipeline.py", "BioGPT/biogpt_pipeline.py"]:
    refactor_file(p)
    print(f"Refactored {p}")
