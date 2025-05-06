import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from app.main import app
from app.db.database import get_supabase
from app.core.security import create_access_token
from app.core.test_config import test_settings


class SupabaseMock:
    """Mock Supabase client for testing."""
    
    def __init__(self):
        self.tables = {
            "users": MockTable("users"),
            "posts": MockTable("posts"),
            "comments": MockTable("comments"),
            "likes": MockTable("likes"),
            "follows": MockTable("follows"),
            "hashtags": MockTable("hashtags"),
            "post_hashtags": MockTable("post_hashtags"),
            "user_saved_posts": MockTable("user_saved_posts"),
            "notifications": MockTable("notifications"),
            "challenges": MockTable("challenges"),
            "challenge_participants": MockTable("challenge_participants"),
            "challenge_achievements": MockTable("challenge_achievements"),
            "challenge_categories": MockTable("challenge_categories"),
        }
        
        # Test data setup
        self.test_users = [
            {
                "id": str(uuid4()),
                "username": "testuser",
                "email": "test@example.com",
                "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW", # "password"
                "full_name": "Test User",
                "bio": "Test bio",
                "avatar_url": "https://example.com/avatar.jpg",
                "created_at": datetime.now().isoformat() - timedelta(hours=1), # 1 hour ago
                "updated_at": datetime.now().isoformat(),
            }
        ]
        self.tables["users"].data = self.test_users
    
    def table(self, name):
        """Get a mocked table by name."""
        return self.tables.get(name, MockTable(name))
    
    def storage(self):
        """Get a mocked storage bucket."""
        return MockStorage()


class MockTable:
    """Mock table implementation for testing."""
    
    def __init__(self, name):
        self.name = name
        self.data = []
        self._filters = []
        self._order_by = None
        self._order_desc = False
        self._range = None
        self._count = None
        self._in_filter = None
    
    def select(self, *columns, count=None):
        """Mock select method."""
        self._count = count
        return self
    
    def eq(self, column, value):
        """Mock equality filter."""
        self._filters.append((column, value, "eq"))
        return self
    
    def in_(self, column, values):
        """Mock in filter."""
        self._in_filter = (column, values)
        return self
    
    def order(self, column, desc=False):
        """Mock order method."""
        self._order_by = column
        self._order_desc = desc
        return self
    
    def range(self, start, end):
        """Mock range method."""
        self._range = (start, end)
        return self
    
    def insert(self, data):
        """Mock insert method."""
        if isinstance(data, dict):
            if "id" not in data:
                data["id"] = str(uuid4())
            self.data.append(data)
            return self
        elif isinstance(data, list):
            for item in data:
                if "id" not in item:
                    item["id"] = str(uuid4())
                self.data.append(item)
            return self
        return self
    
    def update(self, data):
        """Mock update method."""
        self._update_data = data
        return self
    
    def delete(self):
        """Mock delete method."""
        return self
    
    def execute(self):
        """Execute the mock query and return results."""
        result = self.data.copy()
        
        # Apply filters
        for column, value, operator in self._filters:
            if operator == "eq":
                result = [r for r in result if r.get(column) == value]
        
        # Apply in filter
        if self._in_filter:
            column, values = self._in_filter
            result = [r for r in result if r.get(column) in values]
        
        # Apply order
        if self._order_by:
            result.sort(key=lambda x: x.get(self._order_by, ""), reverse=self._order_desc)
        
        # Apply range
        if self._range:
            start, end = self._range
            result = result[start:end+1]
        
        # Handle update
        if hasattr(self, '_update_data'):
            for column, value, operator in self._filters:
                if operator == "eq":
                    for i, item in enumerate(self.data):
                        if item.get(column) == value:
                            self.data[i] = {**item, **self._update_data}
                            # Return the updated item
                            return MockResponse(data=[self.data[i]], count=1)
        
        response = MockResponse(data=result, count=len(result))
        return response


class MockStorage:
    """Mock storage implementation for testing."""
    
    def from_path(self, path):
        """Mock from_path method."""
        bucket = MockBucket()
        return bucket


class MockBucket:
    """Mock storage bucket implementation for testing."""
    
    def upload(self, file_path, file_options):
        """Mock upload method."""
        return {"Key": f"uploads/{os.path.basename(file_path)}"}
    
    def remove(self, paths):
        """Mock remove method."""
        return {"deleted": paths}


class MockResponse:
    """Mock Supabase response."""
    
    def __init__(self, data=None, count=None, error=None):
        self.data = data if data is not None else []
        self.count = count
        self.error = error


@pytest.fixture
def supabase_mock():
    """Fixture for mocked Supabase client."""
    return SupabaseMock()


@pytest.fixture
def client(supabase_mock):
    """Test client fixture with mocked dependencies."""
    
    def get_supabase_override():
        return supabase_mock
    
    app.dependency_overrides[get_supabase] = get_supabase_override
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user():
    """Test user fixture."""
    return {
        "id": str(uuid4()),
        "username": "testuser",
        "email": "test@example.com",
        "password": "password",
        "full_name": "Test User",
        "bio": "Test bio",
        "avatar_url": "https://example.com/avatar.jpg",
    }


@pytest.fixture
def auth_headers(test_user):
    """Auth headers fixture for authenticated requests."""
    access_token = create_access_token(
        subject=test_user["id"],
        expires_delta=timedelta(minutes=test_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"Authorization": f"Bearer {access_token}"} 