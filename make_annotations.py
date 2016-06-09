import pdfextraction.ocr_pipeline
import pickle

with open('breakdowns.pkl', 'r') as f:
    book_breakdowns = pickle.load(f)

print(book_breakdowns.keys())

with open('pdfs/page_ranges.csv') as f:
    ranges = f.readlines()
range_lookup = {line.split(' ')[0]:[int(num) for num in line.strip().split(' ')[1:]] for line in ranges}

# for tbt in book_breakdowns['spectrum_sci']:
    # pdfextraction.ocr_pipeline.perform_ocr(tbt, 'annotations', range_lookup[tbt])

# for tbt in book_breakdowns['workbooks']:
    # pdfextraction.ocr_pipeline.perform_ocr(tbt, 'annotations', range_lookup[tbt])

# for tbt in book_breakdowns['misc'][:-1]:
    # print(tbt)
print(book_breakdowns['misc'])
manual_book = 'The_New_Childrens_Encyclopedia_DK_Publishing.pdf'
pdfextraction.ocr_pipeline.perform_ocr(manual_book:, 'annotations', range_lookup[book_breakdowns['misc'][0]])

