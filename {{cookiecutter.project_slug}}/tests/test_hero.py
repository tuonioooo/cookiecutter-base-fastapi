import pytest
from app.models.hero import Hero
from tests.test_base import TestBase


class TestHeroAPI(TestBase):
    """Test class for Hero API endpoints"""

    # 自动应用的 fixture，不需要在测试函数中传入
    @pytest.fixture(scope="module", autouse=True)
    def setup_db(self):
        print("Creating tables...")
        # 先创建Prompt相关的表，再创建Hero表，确保依赖关系正确
        Hero.metadata.create_all(bind=self.engine)  # 创建数据库表
        yield
        print("Dropping tables...")
        Hero.metadata.drop_all(bind=self.engine)  # 清理数据库表

    def test_create_hero(self, client):
        hero_data = {"name": "Superman", "age": 30, "secret_name": "Clark Kent"}
        response = client.post("/api/v1/heroes/", json=hero_data)
        assert response.status_code == 200
        assert response.json()["name"] == hero_data["name"]
        assert response.json()["age"] == hero_data["age"]
    
    def test_get_heroes(self, client):
        """Test getting all heroes with pagination"""
        hero_data = {"name": "Superman", "age": 30, "secret_name": "Clark Kent"}
        response = client.post("/api/v1/heroes/", json=hero_data)
        hero_id = response.json()["id"]

        # Get the hero we just created
        response = client.get(f"/api/v1/heroes/get/{hero_id}")
        assert response.status_code == 200
        assert response.json()["id"] == hero_id
        assert response.json()["name"] == hero_data["name"]
        assert response.json()["age"] == hero_data["age"]

    def test_get_hero_by_id(self, client):
        """Test getting a single hero by ID"""
        response = client.get(f"{self.API_PREFIX}/heroes/get/1")
        assert response.status_code == 200
        hero = response.json()
        assert hero["id"] == 1
        assert hero["name"] == "Superman"
        assert hero["secret_name"] == "Clark Kent"

    def test_get_hero_not_found(self, client):
        """Test getting a nonexistent hero"""
        response = client.get(f"{self.API_PREFIX}/heroes/get/999")
        assert response.status_code == 404
        error = response.json()
        assert error["code"] == -1
    
    def test_update_hero(self, client):
        """Test updating an existing hero"""
        # First get an existing hero
        get_response = client.get(f"{self.API_PREFIX}/heroes/get/1")
        assert get_response.status_code == 200
        hero = get_response.json()
        
        # Update the hero
        update_data = {
            "name": "蜘蛛侠(更新版)",
            "age": 19
        }
        response = client.put(f"{self.API_PREFIX}/heroes/update/{hero['id']}", json=update_data)
        assert response.status_code == 200
        updated_hero = response.json()
        assert updated_hero["id"] == hero["id"]
        assert updated_hero["name"] == update_data["name"]
        assert updated_hero["age"] == update_data["age"]
    
    def test_delete_hero(self, client):
        """Test deleting an existing hero"""
        hero_data = {"name": "Flash", "age": 28, "secret_name": "BarryAllen"}
        response = client.post("/api/v1/heroes/", json=hero_data)
        hero_id = response.json()["id"]

        response = client.delete(f"/api/v1/heroes/delete/{hero_id}")
        assert response.status_code == 200

    def test_pagination(self, client):
        """Test pagination with offset and limit parameters"""
        # Create multiple test heroes for pagination
        for i in range(5):
            hero_data = {"name": f"Hero{i}", "age": 20 + i, "secret_name": f"Secret{i}"}
            client.post(f"{self.API_PREFIX}/heroes/", json=hero_data)
        
        # Test different pagination combinations
        test_cases = [(0, 2), (2, 2), (4, 1)]
        for offset, limit in test_cases:
            response = client.get(f"{self.API_PREFIX}/heroes?offset={offset}&limit={limit}")
            assert response.status_code == 200
            heroes = response.json()
            # 验证返回的英雄数量不超过limit
            assert len(heroes) <= limit