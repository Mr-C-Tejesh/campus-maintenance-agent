import unittest
from app.main import get_app_status

class TestAppStatus(unittest.TestCase):
    def test_app_status(self):
        status = get_app_status()
        self.assertEqual(status["status"], "ok")
        self.assertIn("Campus/Facility Infrastructure", status["service"])
        
    def test_imports(self):
        import app.main
        self.assertIsNotNone(app.main)

if __name__ == '__main__':
    unittest.main()
