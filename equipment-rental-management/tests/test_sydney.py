def create_equipment(client, name="Drill", total_units = 2):
    response = client.post("/equipment", json = {
        "name": name,
        "category": "Tools",
        "total_units": total_units,
    })
    assert response.status_code == 201
    return response.get_json()

def test_create_equipment_saves_correct_fields(client):
    item = create_equipment(client, total_units = 3)

    response = client.get(f"/equipment/{item['id']}")
    assert response.status_code == 200
    saved = response.get_json()

    assert saved["id"] == item["id"]
    assert saved["name"] == "Drill"
    assert saved["category"] == "Tools"
    assert saved["total_units"] == 3
    assert saved["available_units"] == 3
    assert saved["is_available"] is True

def test_list_equipment_contains_both_items(client):
    first = create_equipment(client, name = "Drill")
    second = create_equipment(client, name = "Ladder")

    response = client.get("/equipment")
    assert response.status_code == 200
    records = response.get_json()

    assert len(records) == 2
    assert {item["id"] for item in records} == {
        first["id"], second["id"]
    }
    assert {item["name"] for item in records} == {"Drill", "Ladder"}

def test_get_nonexistent_equipment_returns_error(client):
    response = client.get("/equipment/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}