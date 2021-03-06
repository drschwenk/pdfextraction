# coding: utf-8
import pickle
import boto
import pandas as pd
import json
import jsonschema
from collections import defaultdict
from copy import deepcopy
import boto.mturk.connection as tc
import boto.mturk.question as tq
from boto.mturk.qualification import PercentAssignmentsApprovedRequirement, Qualifications, Requirement
import requests

# from annotation_schema import page_schema


def load_book_info():
    with open('breakdowns.pkl', 'rb') as f:
        book_breakdowns = pickle.load(f)

    with open('pdfs/page_ranges.csv') as f:
        ranges = f.readlines()
    range_lookup = {line.split(' ')[0]:[int(num) for num in line.strip().split(' ')[1:]] for line in ranges}
    return book_breakdowns, range_lookup


def form_hit_url(book_name, page_n):
    book_name_no_ext = book_name.replace('.pdf', '_')
    # base_url = 'https://s3-us-west-2.amazonaws.com/ai2-vision-turk-data/textbook-annotation-test/textbook_hit_instructions/instructions.html'
    base_url = 'https://s3-us-west-2.amazonaws.com/ai2-vision-turk-data/textbook-annotation-test/build/index.html'
    full_url = base_url + '?url={}{}.jpeg&id={}'.format(book_name_no_ext, page_n, page_n)
    return full_url


def make_book_group_urls(book_groups, book_group, ranges):
    group_urls = []

    def get_start_end(start, end):
        return start, end
    
    for tb in book_groups[book_group]:
        start, end = get_start_end(*ranges[tb])
        for page_n in range(start, end):
            group_urls.append(form_hit_url(tb, page_n))
    return group_urls


def build_hit_params(url, static_params):
    def build_qualifications():
        qualifications = Qualifications()
        req1 = PercentAssignmentsApprovedRequirement(comparator="GreaterThan", integer_value="95")
        qualifications.add(req1)
        return qualifications
    
    hit_params = deepcopy(static_params)
    hit_params['qualifications'] = build_qualifications()
    hit_params['questionform'] = tq.ExternalQuestion(url, static_params['frame_height'])
    hit_params['reward'] = boto.mturk.price.Price(hit_params['amount'])
    return hit_params


def create_single_hit(mturk_connection, url, static_hit_params):
    """
    creates a single HIT from a provided url
    """
    hit_params = build_hit_params(url, static_hit_params)
    create_hit_result = mturk_connection.create_hit(
        title=hit_params['title'],
        description=hit_params['description'],
        keywords=hit_params['keywords'],
        question=hit_params['questionform'],
        reward=hit_params['reward'],
        max_assignments=hit_params['max_assignments'],
        duration=hit_params['duration'],
        qualifications=hit_params['qualifications'],
        lifetime=hit_params['lifetime']
    )
    return create_hit_result


def create_hits_from_pages(mturk_connection, page_links, static_hit_params):
    for url in page_links:
        create_single_hit(mturk_connection, url, static_hit_params)
    

def delete_all_hits(mturk_connection):
    my_hits = list(mturk_connection.get_all_hits())
    for hit in my_hits:
        mturk_connection.disable_hit(hit.HITId)


def count_pages_in_df(any_result_df):
    return len(pd.unique(any_result_df['page']))


def count_pages_with_cat(consensus_df, category):
    return len(pd.unique(consensus_df[consensus_df['category'] == category]['page']))


def delete_some_hits(mturk_connection, hit_ids):
    for hit in hit_ids.keys():
        mturk_connection.disable_hit(hit)


def get_completed_hits(mturk_connection):
    reviewable_hits = []
    page_n = 1
    hits_left = True
    while hits_left:
        hit_range = mturk_connection.get_reviewable_hits(page_size=100, page_number=page_n)
        if not hit_range:
            hits_left = False
            break
        reviewable_hits.extend(hit_range)
        page_n += 1
    return reviewable_hits


def get_assignments(mturk_connection, reviewable_hits, status=None):
    assignments = defaultdict(list)
    for hit in reviewable_hits:
        assignment = mturk_connection.get_assignments(hit.HITId, status=status)
        assignments[hit.HITId].extend(assignment)
    return assignments


def process_raw_hits(assignments_by_hit):
    mechanical_turk_results = defaultdict(list)
    for hit_id, hit_assignments in assignments_by_hit.items():
        for assignment in hit_assignments:
            for answers in assignment.answers:
                box_result = answers[1].fields[0]
                box_json = json.loads(box_result)
                for box in box_json:
                    box['worker_id'] = assignment.WorkerId
                mechanical_turk_results[hit_id].append({
                    assignment.AssignmentId: {answers[0].fields[0]: box_json}}
                )
    return mechanical_turk_results


def accept_hits(mturk_connection, assignments_to_approve):
    for assignment in assignments_to_approve:
        if assignment.AssignmentStatus == 'Submitted':
            mturk_connection.approve_assignment(assignment.AssignmentId)
        else:
            pass
            # print(assignment.AssignmentStatus)


def match_workers_assignments(worker_list, worker_result_df):
    match_df = worker_result_df[worker_result_df['worker_id'].isin(worker_list)]
    return pd.unique(match_df['assignment_id']).tolist(), pd.unique(match_df['worker_id']).tolist()


def reject_assignments(mturk_connection, workers_to_reject, worker_result_df):
    feedback_message = """
    Your HITs contained many incomplete or incorrect pages.
    """
    assignments_to_reject, workers_rejected = match_workers_assignments(workers_to_reject, worker_result_df)
    reject_count = len(assignments_to_reject)
    worker_count = len(workers_rejected)
    for assignment_id in assignments_to_reject:
        try:
            mturk_connection.reject_assignment(assignment_id, feedback_message)
        except boto.mturk.connection.MTurkRequestError:
            print('assignment ' + str(assignment_id) + ' already accepted or rejected')

    return reject_count, worker_count


def ban_bad_workers(mturk_connection, worker_ids):
    for worker in worker_ids:
        reason_for_block = """
        Worker's submissions were largely incomplete.
        """
        print('blocking ' + str(worker))
        mturk_connection.block_worker(worker, reason_for_block)


def get_assignment_statuses(assignment_results):
    assignment_status = []
    for hit_id, assignments in assignment_results.items():
        for assignment in assignments:
            assignment_status.append(assignment.AssignmentStatus)
    status_series = pd.Series(assignment_status)
    return status_series.value_counts()


def make_results_df(raw_hit_results):
    col_names = ['page', 'category', 'hit_id', 'assignment_id', 'box_id', 'worker_id']
    results_df = pd.DataFrame(columns=col_names)
    for hit_id, assignments in raw_hit_results.items():
        for assignment in assignments:
            for a_id, annotation in assignment.items():
                for page, labeled_text in annotation.items():
                    for box in labeled_text:
                        results_df.loc[len(results_df)] = \
                            [page, box['category'], hit_id, a_id, box['id'], box['worker_id']]
    return results_df


def make_question_results_df(raw_hit_results):
    col_names = ['page', 'category', 'hit_id', 'assignment_id', 'box_id', 'worker_id', 'group_n']
    results_df = pd.DataFrame(columns=col_names)
    for hit_id, assignments in raw_hit_results.items():
        for assignment in assignments:
            for a_id, annotation in assignment.items():
                for page, labeled_text in annotation.items():
                    for box in labeled_text:
                        if 'group_n' in box.keys():
                            group_n = box['group_n']
                        else:
                            group_n = 0
                        results_df.loc[len(results_df)] = \
                            [page, box['category'], hit_id, a_id, box['id'], box['worker_id'], str(group_n)]
    return results_df


def make_consensus_df(results_df, no_consensus_flag):
    grouped_by_page = results_df.groupby(['page', 'box_id'])
    aggregated_df = grouped_by_page.agg(pd.DataFrame.mode)
    aggregated_df.drop(['assignment_id', 'page', 'box_id', 'worker_id'], axis=1, inplace=True)
    aggregated_df = aggregated_df.fillna(no_consensus_flag)
    consensus_results_df = aggregated_df.reset_index()
    consensus_results_df.drop('level_2', axis=1, inplace=True)
    return consensus_results_df


def make_consensus_df_w_worker_id(combined_results_df, combined_consensus_results_df):
    consensus_with_worker_id_df = pd.DataFrame(columns=list(combined_consensus_results_df.columns) + ['worker_id', 'consensus_category'])
    for hitbox_id, rows in combined_results_df.groupby(['hit_id', 'box_id']):
        this_consensus_row = combined_consensus_results_df[
            (combined_consensus_results_df['hit_id'] == hitbox_id[0]) & (combined_consensus_results_df['box_id'] == hitbox_id[1])]
        new_rows = rows.copy()
        new_rows['consensus_category'] = this_consensus_row['category'].values[0]
        consensus_with_worker_id_df = consensus_with_worker_id_df.append(new_rows)
    return consensus_with_worker_id_df


def form_annotation_url(page_name, anno_dir):
    file_path = base_path + anno_dir
    return file_path + page_name.replace('jpeg', 'json')


def load_local_annotation(page_name, anno_dir):
    file_path = base_path + anno_dir + page_name.replace('jpeg', 'json')
    try:
        with open(file_path, 'r') as f:
            local_annotations = json.load(f)
    except IOError as e:
        print(e)
        local_annotations = None
    return local_annotations


def process_annotation_results(anno_page_name, boxes, unannotated_page, annotations_folder, page_schema):
    question_cats = ['Multiple Choice',
                     'Fill-in-the-Blank',
                     'Short Answer',
                     'Discussion']

    def update_box(result_row):
        box_id = result_row['box_id']
        category = result_row['category']
        # group_n = result_row['group_n'] # this change is for the simpler question annotation task
        group_n = 0
        try:
            if box_id[0] == 'Q':
                annotation_type = 'question'
                unannotated_page[annotation_type][box_id]['category'] = category
                unannotated_page[annotation_type][box_id]['group_n'] = group_n
            elif category in question_cats:
                old_annotation_type = 'text'
                new_annotation_type = 'question'
                new_id = box_id.replace('T', 'Q')
                unannotated_page[new_annotation_type][new_id] = unannotated_page[old_annotation_type][box_id]
                unannotated_page[new_annotation_type][new_id]['category'] = category
                unannotated_page[new_annotation_type][new_id]['group_n'] = group_n
                unannotated_page[new_annotation_type][new_id]['box_id'] = new_id
                # print unannotated_page[old_annotation_type][box_id]
                del unannotated_page[old_annotation_type][box_id]
        except KeyError as e:
            print(e)
            # if box_id[0] == 'T':
            #     annotation_type = 'question'
            #     group_n = result_row['group_n']
            #     unannotated_page[annotation_type][box_id.replace('T', 'Q')]['category'] = category
            #     unannotated_page[annotation_type][box_id.replace('T', 'Q')]['group_n'] = group_n
            # elif box_id[0] == 'Q':
            #     annotation_type = 'text'
            #     group_n = result_row['group_n']
            #     unannotated_page[annotation_type][box_id.replace('Q', 'T')]['category'] = category
            #     unannotated_page[annotation_type][box_id.replace('Q', 'T')]['group_n'] = group_n
    boxes.apply(update_box, axis=1)
    # validator = jsonschema.Draft4Validator(page_schema)
#     validator.validate(json.loads(json.dumps(unannotated_page)))
    file_path = annotations_folder + anno_page_name.replace('jpeg', 'json').replace("\\", "")
    with open(file_path, 'wb') as f:
        json.dump(unannotated_page, f, indent=4, sort_keys=True)
    return


def write_consensus_results(page_name, boxes, local_result_path, anno_dir):
    unaltered_annotations = load_local_annotation(page_name, anno_dir)
    if unaltered_annotations:
        process_annotation_results(page_name, boxes, unaltered_annotations, local_result_path, page_schema)


def write_results_df(aggregate_results_df, anno_dir, local_result_dir='newly-labeled-annotations/'):
    local_result_path = base_path + local_result_dir
    for page, boxes in aggregate_results_df.groupby('page'):
        write_consensus_results(page, boxes, local_result_path, anno_dir)


def review_results(pages_to_review, annotation_dir='newly-labeled-annotations/'):
    review_api_endpoint = 'http://localhost:8080/api/review'
    payload = {'pages_to_review': str(pages_to_review), 'annotation_dir': annotation_dir}
    headers = {'content-type': 'application/json'}
    return requests.post(review_api_endpoint, data=json.dumps(payload), headers=headers)


def pickle_this(results_df, file_name):
    with open(file_name, 'w') as f:
        pickle.dump(results_df, f)

base_path = '/Users/schwenk/wrk/notebooks/stb/ai2-vision-turk-data/textbook-annotation-test/'
