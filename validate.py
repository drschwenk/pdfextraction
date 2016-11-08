#!/usr/bin/env python3

import os.path
from collections import defaultdict
from collections import Counter
import copy
from pprint import pprint
import warnings
import glob
import json
import sys
import argparse
import re
import jsonschema
from io import StringIO
from .ck12_new_schema import ck12_schema as flat_schema


class DataSetIntegrityChecker(object):
    """
    validate ck12 dataset using the jsonschema defined below
    """

    def __init__(self, data_root_dir, data_file, schema=flat_schema):
        self.data_root_dir = data_root_dir
        self.data_json_file = data_file
        self.schema = schema
        self.dataset = None
        self.max_depth = 4
        self.checks_to_make = {
            'global_ids': self.check_global_ids,
            'image_paths': self.check_image_paths
        }
        self.global_ids_seen = defaultdict(list)

    def load_dataset(self):
        with open(os.path.join(self.data_root_dir, self.data_json_file), 'r') as f:
            self.dataset = json.load(f)

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

    def iterate_over_lessons(self):
        errors = {}
        # for lesson in self.dataset:
        for lesson in self.dataset[:10]:
            for check_type, check in self.checks_to_make.items():
                errors[check_type] = check(lesson)
        self.check_global_counts()
        return errors

    def check_global_counts(self):
        if 'global_ids' in self.checks_to_make.keys():
            for id_type, id_list in self.global_ids_seen.items():
                return id_type + ' global id mismatch'
        else:
            return None

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
        # schema_errors = self.validate_schema()
        # all_errors['schema'] = schema_errors
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
        image_paths = list(self.dict_key_extract('imagePath', lesson))
        for rel_path in image_paths:
            file_path = os.path.join(self.data_root_dir, rel_path)
            print(file_path)

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
        warning_pattern = re.compile('validate.py:\d+:\s+UserWarning:\s+(.+)\s+[0-9]+\.png')
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



