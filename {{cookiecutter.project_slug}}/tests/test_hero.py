from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.models.hero import Hero


class TestHeroAPI:
    """Test class for Hero API endpoints"""
    
    def test_get_heroes(self, client):
        """Test getting all heroes with pagination"""
        response = client.get("/heroes")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_get_heroes_with_filter(self, client):
        """Test filtering heroes by name"""
        response = client.get("/heroes?name=钢铁侠")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any("钢铁侠" in hero["name"] for hero in data["items"])
    
    def test_get_hero_by_id(self, client):
        """Test getting a single hero by ID"""
        response = client.get("/heroes/1")
        assert response.status_code == 200
        hero = response.json()
        assert hero["id"] == 1
        assert hero["name"] == "钢铁侠"
        assert hero["secret_name"] == "托尼·斯塔克"
    
    def test_get_hero_not_found(self, client):
        """Test getting a nonexistent hero"""
        response = client.get("/heroes/999")
        assert response.status_code == 404
        error = response.json()
        assert "未找到ID为999的英雄" in error["detail"]
    
    def test_create_hero(self, client, hero_payload):
        """Test creating a new hero"""
        response = client.post("/heroes", json=hero_payload)
        assert response.status_code == 200
        created_hero = response.json()
        assert created_hero["name"] == hero_payload["name"]
        assert created_hero["age"] == hero_payload["age"]
        assert created_hero["secret_name"] == hero_payload["secret_name"]
        assert "id" in created_hero
    
    def test_update_hero(self, client):
        """Test updating an existing hero"""
        # First get an existing hero
        get_response = client.get("/heroes/2")
        assert get_response.status_code == 200
        hero = get_response.json()
        
        # Update the hero
        update_data = {
            "name": "蜘蛛侠(更新版)",
            "age": 19
        }
        response = client.put(f"/heroes/{hero['id']}", json=update_data)
        assert response.status_code == 200
        updated_hero = response.json()
        assert updated_hero["id"] == hero["id"]
        assert updated_hero["name"] == update_data["name"]
        assert updated_hero["age"] == update_data["age"]
        assert updated_hero["secret_name"] == hero["secret_name"]  # unchanged
    
    def test_update_hero_not_found(self, client):
        """Test updating a nonexistent hero"""
        update_data = {"name": "不存在的英雄"}
        response = client.put("/heroes/999", json=update_data)
        assert response.status_code == 404
        error = response.json()
        assert "未找到ID为999的英雄" in error["detail"]
    
    def test_delete_hero(self, client, hero_payload):
        """Test deleting an existing hero"""
        # Create a hero to delete
        create_response = client.post("/heroes", json=hero_payload)
        assert create_response.status_code == 200
        hero_id = create_response.json()["id"]
        
        # Delete the hero
        response = client.delete(f"/heroes/{hero_id}")
        assert response.status_code == 200
        result = response.json()
        assert f"英雄 ID {hero_id} 已成功删除" == result["message"]
        
        # Verify the hero is deleted
        get_response = client.get(f"/heroes/{hero_id}")
        assert get_response.status_code == 404
    
    def test_delete_hero_not_found(self, client):
        """Test deleting a nonexistent hero"""
        response = client.delete("/heroes/999")
        assert response.status_code == 404
        error = response.json()
        assert "未找到ID为999的英雄" in error["detail"]
    
    @pytest.mark.parametrize("page,page_size", [(1, 2), (2, 2), (3, 1)])
    def test_pagination(self, client, page, page_size):
        """Test pagination with different page and page_size values"""
        response = client.get(f"/heroes?page={page}&page_size={page_size}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= page_size 




# @pytest.fixture
# def client():
#     with TestClient(app) as client:
#         yield client


# def test_get_hero_by_id(client: TestClient):
#         """Test getting a single hero by ID"""
#         response = client.get("/heroes/1")
#         assert response.status_code == 200
#         hero = response.json()
#         assert hero["id"] == 1
#         assert hero["name"] == "钢铁侠"
#         assert hero["secret_name"] == "托尼·斯塔克"