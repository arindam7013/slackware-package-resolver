import unittest
import sys
import os
import re


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from resolver import Resolver

class TestResolver(unittest.TestCase):

    def setUp(self):
        """This method is run before each test to set up the resolver."""
        self.resolver = Resolver(db_path='database.json')

    def test_topsort_simple_success(self):
        """Tests if the topological sort handles a simple case correctly."""
        print("\nRunning: test_topsort_simple_success")
        packages = ['wget']
        result = self.resolver.resolve_with_topsort(packages)

        
        self.assertIn('wget', result)
        self.assertIn('openssl-3.0', result)
        self.assertEqual(len(result), 2)

        
        self.assertLess(result.index('openssl-3.0'), result.index('wget'))

    def test_sat_resolves_simple_case(self):
        """Tests if the SAT solver handles a simple case correctly."""
        print("\nRunning: test_sat_resolves_simple_case")
        packages = ['wget']
        result = self.resolver.resolve_with_sat(packages)
        
        self.assertIn('wget', result)
        self.assertIn('openssl-3.0', result)
        self.assertEqual(len(result), 2)

    def test_sat_conflict_provides_detailed_error(self):
        """Tests if the SAT solver provides a detailed error message on conflict."""
        print("\nRunning: test_sat_conflict_provides_detailed_error")
        packages = ['photo-editor', 'video-encoder']
        
        
        expected_error_regex = (
            r"Multiple versions of 'openssl' are required"
            r".*'openssl-1.1' \(required by 'photo-editor'\)"
            r".*'openssl-3.0' \(required by 'video-encoder'\)"
        )

        
        with self.assertRaisesRegex(RuntimeError, re.compile(expected_error_regex, re.DOTALL)):
            self.resolver.resolve_with_sat(packages)

if __name__ == '__main__':
    unittest.main()