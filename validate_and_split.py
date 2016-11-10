#!/usr/bin/env python3

import os.path
from collections import defaultdict
from collections import Counter
import copy
from pprint import pprint
import warnings
import glob
from sklearn.model_selection import train_test_split
import numpy as np
import json
import sys
import argparse
import re
import jsonschema
from io import StringIO
from .ck12_new_schema import ck12_schema as flat_schema


class DataSetCommonTools(object):

    def __init__(self, data_root_dir, data_file):
        self.data_root_dir = data_root_dir
        self.data_json_file = data_file
        self.dataset = None

    def dict_key_extract(self, key, var):
        if hasattr(var, 'items'):
            for k, v in var.items():
                if k == key:
                    yield v
                if isinstance(v, dict):
                    for result in self.dict_key_extract(key, v):
                        yield result
                elif isinstance(v, list):
                    for d in v:
                        for result in self.dict_key_extract(key, d):
                            yield result

    def load_dataset(self):
        with open(os.path.join(self.data_root_dir, self.data_json_file), 'r') as f:
            self.dataset = json.load(f)


class DataSetIntegrityChecker(DataSetCommonTools):
    """
    validate ck12 dataset
    """

    def __init__(self, data_root_dir, data_file, schema=flat_schema):
        super(DataSetIntegrityChecker, self).__init__(data_root_dir, data_file)
        self.schema = schema
        self.max_depth = 4
        self.checks_to_make = {
            'global_ids': self.check_global_ids,
            'image_paths': self.check_image_paths
        }
        self.global_ids_seen = defaultdict(list)

    def iterate_over_lessons(self):
        errors = defaultdict(list)
        for lesson in self.dataset:
            for check_type, check in self.checks_to_make.items():
                errors_found = check(lesson)
                if errors_found:
                    errors[check_type] += errors_found
        self.check_global_counts()
        return errors

    def check_global_counts(self):
        if 'global_ids' in self.checks_to_make.keys():
            for id_type, id_list in self.global_ids_seen.items():
                if len(id_list) != int(sorted(id_list)[-1]):
                    warnings.warn('global id mismatch for {}'.format(id_type))
                if len(set(id_list)) != len(id_list):
                    warnings.warn('non unique ids present for {}'.format(id_type))
                    print()
        return self.global_ids_seen

    def validate_schema(self):
        errors = []
        try:
            validator = jsonschema.Draft4Validator(self.schema)
            for error in sorted(list(validator.iter_errors(self.dataset)), key=lambda x: x.absolute_schema_path[0]):
                errors.append([error.message, list(error.absolute_path)[:self.max_depth]])
        except jsonschema.ValidationError as e:
            errors.append("Error in schema --%s-" + e.message)
        return errors

    def validate_dataset(self):
        if not self.dataset:
            self.load_dataset()
        all_errors = {}
        schema_errors = self.validate_schema()
        all_errors['schema'] = schema_errors
        all_errors.update(self.iterate_over_lessons())
        for errors in all_errors.values():
            if errors:
                return all_errors
        return 'all validation test passed'

    def check_global_ids(self, lesson):
        this_lessons_keys = list(self.dict_key_extract('globalID', lesson))
        for k in this_lessons_keys:
            id_type = k.split('_')[0]
            id_num = k.split('_')[1]
            self.global_ids_seen[id_type].append(id_num)

    def check_image_paths(self, lesson):
        missing_images = []
        image_paths = list(self.dict_key_extract('imagePath', lesson))
        for rel_path in image_paths:
            file_path = os.path.join(self.data_root_dir, rel_path)
            if not os.path.exists(file_path):
                missing_images.append(file_path)
        return missing_images


class TestTrainSplitter(DataSetCommonTools):

    def __init__(self, data_root_dir, data_file):
        super(TestTrainSplitter, self).__init__(data_root_dir, data_file)

    def make_debug(self, train_ids, test_ids ):
        debug_train_assignments = []
        for lesson_id in train_ids:
            lesson_name = [lesson['lessonName'] for lesson in self.dataset if lesson['globalID'] == lesson_id][0]
            lesson_meta_id = [lesson['metaLessonID'] for lesson in self.dataset if lesson['globalID'] == lesson_id][0]
            debug_train_assignments.append((lesson_id, lesson_name, lesson_meta_id))
        debug_test_assignments = []
        for lesson_id in test_ids:
            lesson_name = [lesson['lessonName'] for lesson in self.dataset if lesson['globalID'] == lesson_id][0]
            lesson_meta_id = [lesson['metaLessonID'] for lesson in self.dataset if lesson['globalID'] == lesson_id][0]
            debug_test_assignments.append((lesson_id, lesson_name, lesson_meta_id))
        return {'train': debug_train_assignments, 'test': debug_test_assignments}

    def perform_split(self, test_fraction=0.2, manual_assignments={}, debug=False):
        if not self.dataset:
            self.load_dataset()
        meta_lessons = np.array(list(set([lesson['metaLessonID'] for lesson in self.dataset if lesson['metaLessonID']
                                          not in manual_assignments.keys()])))
        meta_train_lessons, meta_test_lessons = train_test_split(meta_lessons, test_size=test_fraction)
        meta_train_lessons = meta_train_lessons.tolist()
        meta_test_lessons = meta_test_lessons.tolist()
        meta_train_lessons += [metalesson for metalesson, lesson_info in manual_assignments.items() if lesson_info['split'] == 'train']
        meta_test_lessons += [metalesson for metalesson, lesson_info in manual_assignments.items() if lesson_info['split'] == 'test']

        train_lessons = [lesson['globalID'] for lesson in self.dataset if lesson['metaLessonID'] in meta_train_lessons]
        test_lessons = [lesson['globalID'] for lesson in self.dataset if lesson['metaLessonID'] in meta_test_lessons]
        if debug:
            debug_info = self.make_debug(train_lessons, test_lessons)
        else:
            debug_info = None
        return {'train': train_lessons, 'test': test_lessons}, debug_info

    def compute_split_stats(self, test_train_assignments, diagram_only=False):
        if not self.dataset:
            self.load_dataset()
        stat_counts = {
            'n_text_questions': {
                'train': 0,
                'test': 0,
                'id_to_find': 'nonDiagramQuestions'
            },
            'n_diagram_questions': {
                'train': 0,
                'test': 0,
                'id_to_find': 'diagramQuestions'
            },
            'n_topics': {
                'train': 0,
                'test': 0,
                'id_to_find': 'topics'
            },
            'n_instructional_diagrams': {
                'train': 0,
                'test': 0,
                'id_to_find': 'instructionalDiagrams'
            },
        }
        if diagram_only:
            diagram_only_split = {k: [lid for lid in v if [al for al in self.dataset if al['globalID'] == lid][0]['instructionalDiagrams']]
                                  for k, v in test_train_assignments.items()}
            test_train_assignments = diagram_only_split
        for split in ['test', 'train']:
            for lesson_id in test_train_assignments[split]:
                for stat_type, stats in stat_counts.items():
                    lesson_content = [lesson for lesson in self.dataset if lesson['globalID'] == lesson_id][0]
                    stats[split] += len(list(self.dict_key_extract(stats['id_to_find'], lesson_content))[0].values())

        stat_counts['n_lessons'] = {
            "test": len(test_train_assignments['test']),
            "train": len(test_train_assignments['train']),
            'id_to_find': 'n_lessons'
        }
        for stat_type, stat in stat_counts.items():
            stat['test_fraction'] = "{0:.3f}".format(stat['test'] / (stat['train'] + stat['test']))
        return stat_counts

    def split_and_compute_stats(self, manual_assignments={}):
        tt_split, debug_tt_splits = self.perform_split(manual_assignments=manual_assignments)
        stats = self.compute_split_stats(tt_split)
        return stats


def main():
    parser = argparse.ArgumentParser(description='Run Shining3 validation tests')
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    args = parser.parse_args()

    if not args.verbose:
        warning_buffer = StringIO()
        saved_stderr = sys.stderr
        sys.stderr = warning_buffer
        warnings = warning_buffer.getvalue()
        warning_buffer.close()
        sys.stderr = saved_stderr
        warning_pattern = re.compile('validate_and_split.py:\d+:\s+UserWarning:\s+(.+)\s+[0-9]+\.png')
        single_warns = re.findall(warning_pattern, warnings)
        warning_counts = Counter()
        for warn in single_warns:
            warning_counts.update([warn])

        print('Summary of warnings'+'\n'*2)
        for warning, count in warning_counts.most_common():
            print('%s, %d occurrences' % (warning, count) + '\n'*2)

    else:
        run_tests()

if __name__ == "__main__":
    main()



