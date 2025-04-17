#!/usr/bin/env python
import os
import json
from datetime import datetime, timedelta, timezone
from jose import jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

print(f"SECRET_KEY length: {len(SECRET_KEY) if SECRET_KEY else 0}")
print(f"ALGORITHM: {ALGORITHM}")

# Create a test token
def create_test_token():
    # Create token with 1 hour expiry
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    expire_timestamp = expire.timestamp()
    
    to_encode = {"exp": expire_timestamp, "sub": "test-user-id"}
    
    try:
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        print(f"\nToken created successfully: {token[:20]}...")
        return token
    except Exception as e:
        print(f"\nError creating token: {str(e)}")
        return None

# Verify a token
def verify_token(token):
    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM]
        )
        print(f"\nToken decoded successfully!")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return True
    except Exception as e:
        print(f"\nToken validation error: {str(e)}")
        return False

# Run the test
if __name__ == "__main__":
    print("\n=== JWT Token Test ===\n")
    
    # Test token creation
    token = create_test_token()
    
    if token:
        # Test token validation
        verify_token(token)
        
        # Test with invalid token
        print("\n--- Testing with invalid token ---")
        invalid_token = token + "invalid"
        verify_token(invalid_token)
        
        # Test with wrong secret key
        print("\n--- Testing with wrong secret key ---")
        try:
            jwt.decode(token, "wrong-secret-key", algorithms=[ALGORITHM])
            print("Token validated with wrong key! This is a security issue.")
        except Exception as e:
            print(f"Correctly failed with wrong key: {str(e)}")
    
    print("\n=== Test Complete ===\n") 