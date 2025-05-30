import os
import unittest
import tempfile
from app import app, init_db, get_db # Assuming app.py contains these

class SurveyAppTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        app.config['DATABASE'] = cls.db_path
        app.config['TESTING'] = True
        # Matplotlib backend needs to be set before any plotting operations,
        # even if they happen in the app code triggered by tests.
        import matplotlib
        matplotlib.use('Agg') # Use a non-interactive backend for tests

        cls.app_context = app.app_context()
        cls.app_context.push()
        init_db() # Initialize the database schema

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()
        os.close(cls.db_fd)
        os.unlink(cls.db_path)

    def setUp(self):
        self.client = app.test_client()
        # Clear previous test data before each test
        with app.app_context(): # Ensure context for get_db
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM results")
            conn.commit()

    def test_index_page_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Survey", response.data)

    def test_submit_data_and_redirects(self):
        response = self.client.post('/submit', data={
            'satisfaction': '5',
            'feedback': 'Very Good'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Very Good", response.data)
        self.assertIn(b"Satisfaction Score Distribution", response.data)
        self.assertIn(b'<img src="data:image/png;base64,', response.data)

    def test_results_page_empty(self):
        response = self.client.get('/results')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No results yet.", response.data)
        # When there are no results, chart_url should be None, so no img tag for chart
        self.assertNotIn(b'<img src="data:image/png;base64,', response.data)
        self.assertNotIn(b"Satisfaction Score Distribution", response.data)


    def test_multiple_submissions_and_chart(self):
        self.client.post('/submit', data={'satisfaction': '1', 'feedback': 'Bad'})
        self.client.post('/submit', data={'satisfaction': '3', 'feedback': 'Ok'})
        self.client.post('/submit', data={'satisfaction': '5', 'feedback': 'Excellent'})

        response = self.client.get('/results')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Bad", response.data)
        self.assertIn(b"Ok", response.data)
        self.assertIn(b"Excellent", response.data)
        self.assertIn(b"Satisfaction Score Distribution", response.data)
        self.assertIn(b'<img src="data:image/png;base64,', response.data)

if __name__ == '__main__':
    unittest.main()
