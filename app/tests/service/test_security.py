import unittest
from core.security import hash_password, verify_password

class TestSecurity(unittest.TestCase):
    def test_password_hashing_and_verification(self):
        print("# TEST PASSWORDS (for development only)")
        print(hash_password('123456')) 

        """Test valid password hashing and verification"""
        plain_password = "SecurePass123!"
        hashed = hash_password(plain_password)

        # Verify correct password
        self.assertTrue(verify_password(plain_password, hashed))
        
        # Verify incorrect password
        self.assertFalse(verify_password("WrongPass456!", hashed))

    def test_unique_salts(self):
        """Test that different hashes are generated for same password"""
        password = "RepeatedPassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        self.assertNotEqual(hash1, hash2)

    def test_complex_password(self):
        """Test handling of complex passwords"""
        complex_pass = "P@ssw0rd!£$%^&*()"
        hashed = hash_password(complex_pass)
        self.assertTrue(verify_password(complex_pass, hashed))

    def test_empty_password(self):
        """Test handling of empty password (should still hash but not recommended)"""
        empty_pass = ""
        hashed = hash_password(empty_pass)
        self.assertTrue(verify_password(empty_pass, hashed))

    def test_invalid_hash_verification(self):
        """Test verification with invalid hash format"""
        with self.assertRaises(ValueError):
            verify_password("password", "invalid_hash_format")

    def test_hash_contains_metadata(self):
        """Test that hash contains bcrypt identifier and cost factor"""
        hashed = hash_password("test")
        self.assertTrue(hashed.startswith("$2b$"))
        self.assertEqual(hashed.split("$")[2][0:2], "12")  # Verify cost factor

if __name__ == '__main__':
    unittest.main()