import pdfparser.poppler as pdf
from collections import defaultdict


def parse_pdf(file_path):
    doc = pdf.Document(file_path)
    page_dict = defaultdict(dict)
    # print 'No of pages', doc.no_of_pages
    for page in doc:
        box_index = 0
        for flow in page:
            for block in flow:
                for line in block:
                    line_dict = {
                        'content': line.text,
                        'rectangle': line.bbox.as_tuple(),
                        'font_size': list(line.char_fonts)[0].size,
                        'font_color': list(line.char_fonts)[0].color.as_tuple()
                    }
                    if sum(line_dict['font_color']) or True:
                        page_dict['P' + str(page.page_no)].update({'T' + str(box_index): line_dict})
                        box_index += 1
    return page_dict

# for p in d:
# #     print 'Page', p.page_no, 'size =', p.size
#     for f in p:
# #         print ' '*1,'Flow'
#         for b in f:
# #             print ' '*2,'Block', 'bbox=', b.bbox.as_tuple()
#             for l in b:
# #                 print ' '*3, l.text.encode('UTF-8'), '(%0.2f, %0.2f, %0.2f, %0.2f)'% l.bbox.as_tuple()
#                 #assert l.char_fonts.comp_ratio < 1.0
#                 print list(l.char_fonts)[0]
# #                 for i in range(len(l.text)):
# #                     print l.text[i].encode('UTF-8'), '(%0.2f, %0.2f, %0.2f, %0.2f)'% l.char_bboxes[i].as_tuple(),\
# #                         print'(%0.2f, %0.2f, %0.2f, %0.2f)'% , \
# #                     print l.text, l.char_fonts[i].size, l.char_fonts[i].color
# #                         l.char_fonts[i].name, l.char_fonts[i].size, l.char_fonts[i].color,
# #                     print '\n'
#                 print