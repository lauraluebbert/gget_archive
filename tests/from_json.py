import unittest
from typing import Callable
import pandas as pd
import sys
import json
import hashlib


_KNOWN_ERRORS = {
    "ValueError": ValueError,
    "RuntimeError": RuntimeError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "AssertionError": AssertionError,
    "AttributeError": AttributeError,
    "NotImplementedError": NotImplementedError
}


def _assert_equal(name: str, td: dict[str, dict[str, ...]], func: Callable) -> Callable:
    def assert_equal(self: unittest.TestCase):
        test = name
        expected_result = td[test]["expected_result"]
        result_to_test = func(**td[test]["args"])
        # If result is a DataFrame, convert to list
        if isinstance(result_to_test, pd.DataFrame):
            result_to_test = result_to_test.dropna(axis=1).values.tolist()

        self.assertEqual(result_to_test, expected_result)
    return assert_equal


def _assert_equal_json_hash(name: str, td: dict[str, dict[str, ...]], func: Callable) -> Callable:
    def assert_equal_json_hash(self: unittest.TestCase):
        test = name
        expected_result = td[test]["expected_result"]
        result_to_test = func(**td[test]["args"])
        # If result is a DataFrame, convert to list
        if isinstance(result_to_test, pd.DataFrame):
            result_to_test = result_to_test.dropna(axis=1).values.tolist()

        result_to_test = json.dumps(result_to_test)
        result_to_test = hashlib.md5(result_to_test.encode()).hexdigest()

        self.assertEqual(result_to_test, expected_result)
    return assert_equal_json_hash


def _assert_equal_nested(name: str, td: dict[str, dict[str, ...]], func: Callable) -> Callable:
    def assert_equal_nested(self: unittest.TestCase):
        test = name
        expected_result = td[test]["expected_result"]
        result_to_test = func(**td[test]["args"])
        # If result is a DataFrame, convert to json (nested dataframes prevent easy listification)
        if isinstance(result_to_test, pd.DataFrame):
            result_to_test = json.loads(
                result_to_test.to_json(orient="records", force_ascii=False)
            )

        self.assertEqual(result_to_test, expected_result)
    return assert_equal_nested


def _assert_equal_json_hash_nested(name: str, td: dict[str, dict[str, ...]], func: Callable) -> Callable:
    def assert_equal_json_hash_nested(self: unittest.TestCase):
        test = name
        expected_result = td[test]["expected_result"]
        result_to_test = func(**td[test]["args"])
        # If result is a DataFrame, convert to json (nested dataframes prevent easy listification)
        if isinstance(result_to_test, pd.DataFrame):
            result_to_test = json.loads(
                result_to_test.to_json(orient="records", force_ascii=False)
            )

        result_to_test = json.dumps(result_to_test)
        result_to_test = hashlib.md5(result_to_test.encode()).hexdigest()

        self.assertEqual(result_to_test, expected_result)
    return assert_equal_json_hash_nested


def _error(name: str, td: dict[str, dict[str, ...]], func: Callable) -> Callable:
    try:
        # noinspection PyPep8Naming
        Error = td[name]["expected_result"]
    except KeyError:
        raise ValueError("Error test must have an 'expected_result' key.")

    if Error not in _KNOWN_ERRORS:
        raise ValueError(f"Unknown error type: {Error}")

    # noinspection PyPep8Naming
    Error = _KNOWN_ERRORS[Error]

    def error(self: unittest.TestCase):
        test = name
        with self.assertRaises(Error):
            func(**td[test]["args"])
    return error


_TYPES: dict[str, Callable[[str, dict[str, dict[str, ...]], Callable], Callable]] = {
    "assert_equal": _assert_equal,
    "assert_equal_json_hash": _assert_equal_json_hash,
    "assert_equal_nested": _assert_equal_nested,
    "assert_equal_json_hash_nested": _assert_equal_json_hash_nested,
    "error": _error
}


def from_json(test_dict: dict[str, dict[str, ...]], func: callable) -> type:
    """
    Create a metaclass that will generate test methods from a (json-loaded) dictionary.
    """
    class C(type):
        def __new__(cls, name: str, bases: tuple[type, ...], dct: dict[str, ...]):
            assert unittest.TestCase in bases, "from_json should only be applied to unittest.TestCase subclasses."
            for k, v in test_dict.items():
                type_ = v["type"]
                if type_ == "code_defined":
                    continue
                if type_ in _TYPES:
                    if not k.startswith("test_"):
                        print(f"Invalid test name: {k}", file=sys.stderr)
                        continue

                    if k in dct:
                        print(f"Duplicate test name: {k}", file=sys.stderr)
                        continue

                    # Create the test method for the given type and add it to the new class
                    dct[k] = _TYPES[type_](k, test_dict, func)
                    print(f"Loaded test {k} of type {type_} from json.")
                else:
                    if k not in dct:
                        raise ValueError(f"Unknown test type: {type_} and no test method defined.")
                    print(f"Unknown test type: {type_}", file=sys.stderr)

            return super().__new__(cls, name, bases, dct)
    return C
