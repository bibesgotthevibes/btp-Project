with open("backend/app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# find where app.run is
if "if __name__ == '__main__':" in text:
    print("Main block exists")

