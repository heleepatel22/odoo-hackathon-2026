import os
import glob

templates_dir = r"c:\Users\HAPPY PATEL\Desktop\vendor\templates"

html_files = glob.glob(os.path.join(templates_dir, "*.html"))

for file_path in html_files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace hardcoded initials
    content = content.replace(">RM<", '><i class="fas fa-user"></i><')
    # Replace hardcoded names
    content = content.replace(">Rahul Mehta<", '>User<')
    # Replace hardcoded emails
    content = content.replace(">rahul.mehta@company.com<", '>user@company.com<')
    # Replace hardcoded roles (in the sidebar usually)
    content = content.replace(">Procurement Officer<", '>Role<')

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Replaced placeholders in {len(html_files)} files.")
