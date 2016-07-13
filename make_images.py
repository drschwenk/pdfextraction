import pdfextraction.ocr_pipeline
import pickle

with open('breakdowns.pkl', 'r') as f:
    book_breakdowns = pickle.load(f)

with open('pdfs/page_ranges.csv') as f:
    ranges = f.readlines()
range_lookup = {line.split(' ')[0]:[int(num) for num in line.strip().split(' ')[1:]] for line in ranges}

for book in book_breakdowns['daily_sci'][4:5]:
    pdfextraction.ocr_pipeline.process_book(book, range_lookup[book], line_overlap=0.5,
                                            word_margin=0.1, char_margin=2.0, line_margin=0.5, boxes_flow=0.5)

# manual_book = 'The_New_Childrens_Encyclopedia_DK_Publishing.pdf'
# pdfextraction.ocr_pipeline.process_book(manual_book, range_lookup[book_breakdowns['misc'][0]], line_overlap=0.5,
#         word_margin=0.1, char_margin=2.0, line_margin=0.5, boxes_flow=0.5)
#