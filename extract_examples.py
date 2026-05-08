import csv
import random
import os

def extract_examples(file_path, num_examples=3):
    # Ensure file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    examples = []
    with open(file_path, 'r', encoding='utf-8') as f:
        # Use tab delimiter since it is a TSV file
        reader = csv.DictReader(f, delimiter='\t')
        
        for row in reader:
            original = row.get('original', '').strip()
            simplified = row.get('english simplified', '').strip()
            
            # Only keep rows that have both fields
            if original and simplified:
                examples.append((original, simplified))
    
    if not examples:
        print("No valid examples found.")
        return

    # Pick a few random examples
    sampled = random.sample(examples, min(num_examples, len(examples)))

    for i, (orig, simp) in enumerate(sampled, 1):
        print(f"\n" + "="*50)
        print(f" EXAMPLE {i} ")
        print("="*50)
        print(f"\n[ ORIGINAL ]\n{orig}")
        print(f"\n[ ENGLISH SIMPLIFIED ]\n{simp}")
        print("\n")

if __name__ == "__main__":
    # Points to data/data.tsv
    target_file = os.path.join(os.path.dirname(__file__), 'data', 'data.tsv')
    extract_examples(target_file, num_examples=3)
