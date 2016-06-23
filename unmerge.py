import json


def box_is_contained(inferior_box, superior_box):
    vertically_contained = inferior_box[0][1] >= superior_box[0][1] and inferior_box[1][1] <= superior_box[1][1]
    horizontally_contained = inferior_box[0][0] >= superior_box[0][0] and inferior_box[1][0] <= superior_box[1][0]
    return vertically_contained and horizontally_contained


def find_constituent_boxes(unmerged_anno, merged_anno_box):
    constituent_boxes = []
    for box_name, box_vals in unmerged_anno['text'].items():
        if box_is_contained(box_vals['rectangle'], merged_anno_box['rectangle']):
            box_vals['category'] = merged_anno_box['category']
            constituent_boxes.append(box_vals)
    return constituent_boxes


def unmerge_boxes_by_category(unmerged_annotations, merged_annotations, box_cat='Question'):
    new_annotations = []
    for box_name, box_val in merged_annotations['text'].items():
        if box_val['category'] == box_cat:
            atomic_boxes = find_constituent_boxes(unmerged_annotations, box_val)
            if atomic_boxes:
                new_annotations.extend(atomic_boxes)
            else:
                new_annotations.append(box_val)
        else:
            new_annotations.append(box_val)
    sorted_boxes = sorted(new_annotations, key=lambda x: x['rectangle'][0][1])
    unmerged_text_named = {'T' + str(i + 1): sorted_boxes[i] for i in range(len(sorted_boxes))}
    for name, detection in unmerged_text_named.items():
        detection['box_id'] = name
    return unmerged_text_named


def write_unmerged_annotations(unmerged_text_anno, new_file_path):
    full_anno = {"text": unmerged_text_anno, "figure": {}, "relationship": {}}
    with open(new_file_path, 'w') as f:
        json.dump(full_anno, f)


def unmerge_boxes_single_page(page_image, base_path, overmerged_dir, unmerged_dir, lessmerged_dir):
    json_file = page_image.replace('.jpeg', '.json')

    merged_anno_path = base_path + overmerged_dir + json_file
    unmerged_anno_path = base_path + unmerged_dir + json_file
    lessmerged_anno_path = base_path + lessmerged_dir + json_file

    with open(merged_anno_path, 'rb') as f:
        merged_anno = json.load(f)
    with open(unmerged_anno_path, 'rb') as f:
        unmerged_anno = json.load(f)

    unmerged_text_boxes = unmerge_boxes_by_category(unmerged_anno, merged_anno)
    write_unmerged_annotations(unmerged_text_boxes, lessmerged_anno_path)


def unmerge_single_textbook(book_name, (start_n, stop_n), base_path, overmerged_dir, unmerged_dir, destination_dir):
    for page_n in range(start_n, stop_n):
        page_image = book_name.replace('.pdf', '') + '_' + str(page_n) + '.jpeg'
        try:
            unmerge_boxes_single_page(page_image, base_path, overmerged_dir, unmerged_dir, destination_dir)
        except IOError as e:
            print e
