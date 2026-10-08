"""Regression checks for long replies and earlier conversation details."""

import unittest

from api.context import select_history
from api.messages import pack
from api.preferences import validate, HISTORY


def turn(question, answer):
    return [{'role': 'user', 'content': question}, {'role': 'assistant', 'content': answer}]


def context(rows, question='continue', reuse=True):
    return select_history(list(reversed(rows)), question, validate(None), reuse)


class HistoryTests(unittest.TestCase):
    def test_long_latest_answer_keeps_its_question_and_answer_ends(self):
        rows = turn('My project is named Cedar.', 'Start of answer ' + 'x' * 20000 + ' end of answer')
        result = context(rows)
        self.assertEqual([r['role'] for r in result], ['user', 'assistant'])
        self.assertIn('Cedar', result[0]['content'])
        self.assertIn('Start of answer', result[1]['content'])
        self.assertIn('end of answer', result[1]['content'])
        self.assertLessEqual(sum(len(r['content']) for r in result), HISTORY['efficient'])

    def test_three_long_turns_survive_in_order(self):
        rows = sum((turn(f'Question {i}', f'Answer {i} ' + 'x' * 20000) for i in range(3)), [])
        result = context(rows)
        self.assertEqual([r['content'] for r in result if r['role'] == 'user'], ['Question 0', 'Question 1', 'Question 2'])
        self.assertLessEqual(sum(len(r['content']) for r in result), HISTORY['efficient'])

    def test_relevant_old_details_survive_many_later_turns(self):
        rows = turn('The launch codename is Cedar, and the budget is 42.', 'Understood.')
        rows += sum((turn(f'Unrelated question {i}', 'Response ' * 250) for i in range(40)), [])
        result = context(rows, 'What was the launch codename and budget?')
        self.assertIn('Cedar', str(result))
        self.assertIn('Unrelated question 39', str(result))
        self.assertLessEqual(sum(len(r['content']) for r in result), HISTORY['efficient'])

    def test_attachment_is_found_beyond_recent_text_window(self):
        document = pack('Read this', documents=['the secret color is violet'], files=[{'name': 'notes.txt'}])
        rows = turn(document, 'Read it.') + sum((turn('Next question', 'x' * 4000) for _ in range(15)), [])
        self.assertIn('secret color is violet', str(context(rows, 'What color was in my file?')))
        self.assertNotIn('secret color is violet', str(context(rows, reuse=False)))

    def test_orphan_answer_is_not_sent(self):
        self.assertEqual(context([{'role': 'assistant', 'content': 'orphan'}]), [])

    def test_short_chat_remains_exact(self):
        rows = turn('hello', 'hi') + turn('My name is Sam', 'Hello Sam')
        self.assertEqual(context(rows), rows)
