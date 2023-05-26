import collections
import os
from typing import Optional

from depmanager.common.shared.progress_bar import ProgressBar


def fuzzy_compare_strings(str_a: str, str_b: str) -> int:
    similarity = collections.Counter(str_a) - collections.Counter(str_b)
    return sum(abs(val) for val in similarity.values())


def select_fuzzy_match(filepath: str, found: list[tuple[str, str]]) -> tuple[Optional[str], Optional[str]]:
    if len(found) == 0:
        return None, None
    if len(found) == 1:
        return found[0]
    fuzzy_matches = [fuzzy_compare_strings(filepath, item[1]) for item in found]
    best_index = fuzzy_matches.index(min(fuzzy_matches))
    return found[best_index]


def find_fuzzy_file_match(
    filepath: str, included_files: list[tuple[str, str, str]], threshold: int = 2
) -> tuple[Optional[str], Optional[str]]:
    filepath_ext = os.path.splitext(filepath)[1]

    found_fuzz_filepath = []
    found_fuzz_file = []
    for repair_var_id, repair_var_file_path, repair_var_file_only in included_files:
        if filepath_ext != os.path.splitext(repair_var_file_only)[1]:
            continue
        if fuzzy_compare_strings(filepath, repair_var_file_path) < threshold:
            found_fuzz_filepath.append((repair_var_id, repair_var_file_path))
        elif fuzzy_compare_strings(filepath, repair_var_file_only) < threshold:
            found_fuzz_file.append((repair_var_id, repair_var_file_path))

    if len(found_fuzz_filepath) > 0:
        return select_fuzzy_match(filepath, found_fuzz_filepath)
    return select_fuzzy_match(filepath, found_fuzz_file)


def remove_empty_directories(filepath):
    progress = ProgressBar(100, description="Removing empty directories")
    progress.inc()
    folders = list(os.walk(filepath))[1:]
    progress.progress_total = len(folders)
    progress.progress_count = 0
    for folder in folders:
        progress.inc()
        if not folder[1] and not folder[2]:
            os.rmdir(folder[0])


def str_in_substrings(str_a: str, str_list: list[str], ignore_case: bool = True) -> list[str]:
    if ignore_case:
        str_a_lower = str_a.lower()
        return [s for s in str_list if str_a_lower in s.lower()]
    return [s for s in str_list if str_a in s]


def is_str_in_substrings(str_a: str, str_list: list[str], ignore_case: bool = True) -> bool:
    return len(str_in_substrings(str_a, str_list, ignore_case)) > 0


def substrings_in_str(str_a: str, str_list: list[str], ignore_case: bool = True) -> list[str]:
    if ignore_case:
        str_a_lower = str_a.lower()
        return [s for s in str_list if s.lower() in str_a_lower]
    return [s for s in str_list if s in str_a]


def are_substrings_in_str(str_a: str, str_list: list[str], ignore_case: bool = True) -> bool:
    return len(substrings_in_str(str_a, str_list, ignore_case)) > 0


def get_file_stat(file_path) -> tuple[str, float, float]:
    stats = os.stat(file_path)
    return (file_path, stats.st_mtime, stats.st_size)
