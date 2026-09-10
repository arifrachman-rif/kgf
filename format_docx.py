import pypandoc
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT

outfile = 'Proposal_Kemitraan_KGF_Dompet_Dhuafa_v2.docx'

# 1. Regenerate from markdown
pypandoc.convert_file('proposal_kemitraan_dompet_dhuafa_final.md', 'docx', outputfile=outfile)

# 2. Modify with python-docx
doc = Document(outfile)

# Set all normal paragraphs to justified
for p in doc.paragraphs:
    if p.style.name == 'Normal' or p.style.name == 'Body Text':
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

# Set page to landscape
for section in doc.sections:
    new_width, new_height = section.page_height, section.page_width
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = new_width
    section.page_height = new_height
    # Reduce margins slightly
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)

# Fix tables
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            # Set padding
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(8)

doc.save(outfile)
print('Document formatted successfully.')
