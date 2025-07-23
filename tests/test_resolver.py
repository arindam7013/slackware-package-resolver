import unittest
import sys
import os
import re

# This adds the project root to the Python path so we can import our resolver
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

        # A topological sort can have multiple valid outputs.
        # Instead of a strict list comparison, we verify the essential properties.
        
        # 1. Check that all required packages are present.
        self.assertIn('wget', result)
        self.assertIn('openssl-3.0', result)
        self.assertEqual(len(result), 2)

        # 2. Check that the dependency comes before the package that needs it.
        self.assertLess(result.index('openssl-3.0'), result.index('wget'))

    def test_sat_resolves_simple_case(self):
        """Tests if the SAT solver handles a simple case correctly."""
        print("\nRunning: test_sat_resolves_simple_case")
        packages = ['wget']
        result = self.resolver.resolve_with_sat(packages)
        # The exact order can vary, so we check for content and length.
        self.assertIn('wget', result)
        self.assertIn('openssl-3.0', result)
        self.assertEqual(len(result), 2)

    def test_sat_conflict_provides_detailed_error(self):
        """Tests if the SAT solver provides a detailed error message on conflict."""
        print("\nRunning: test_sat_conflict_provides_detailed_error")
        packages = ['photo-editor', 'video-encoder']
        
        # We expect the error message to contain these key phrases, in order.
        expected_error_regex = (
            r"Multiple versions of 'openssl' are required"
            r".*'openssl-1.1' \(required by 'photo-editor'\)"
            r".*'openssl-3.0' \(required by 'video-encoder'\)"
        )

        # Use assertRaisesRegex to check both the error type and its message content.
        # The re.DOTALL flag allows '.' to match newlines, making the regex simpler.
        with self.assertRaisesRegex(RuntimeError, re.compile(expected_error_regex, re.DOTALL)):
            self.resolver.resolve_with_sat(packages)

if __name__ == '__main__':
    unittest.main()