import unittest

from main import batch_estimate_probability_of_change


class MockRequest(object):

    def get_json(self, silent):
        return [
            {
                "name": "FB",
                "days": 3,
                "percent_change": 2
            }
        ]


class TestEstimatedMethods(unittest.TestCase):

    def test_batch_estimate_probability_of_change(self):
        result = batch_estimate_probability_of_change(MockRequest())
        self.assertTrue(len(result) > 0)


if __name__ == '__main__':
    unittest.main()
