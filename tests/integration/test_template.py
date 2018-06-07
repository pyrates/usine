from io import StringIO
from pathlib import Path

from usine import template


def test_with_filepath_as_string():
    assert template('tests/template.txt', what='text').read() == \
        'This is a text file.\n'


def test_with_filepath_as_path():
    assert template(Path('tests/template.txt'), what='text').read() == \
        'This is a text file.\n'


def test_with_stringio():
    assert template(StringIO('This is a $$what.'), what='text').read() == \
        'This is a text.'


def test_with_extra_context():
    assert template(StringIO('A $$what.'), what='text', extra='ok').read() == \
        'A text.'


def test_in_a_middle_of_a_string():
    assert template(StringIO('A $${what}ever.'), what='text').read() == \
        'A textever.'


def test_with_non_identifier_bracket():
    assert template(StringIO('A ${what}ever.'), what='text').read() == \
        'A ${what}ever.'
