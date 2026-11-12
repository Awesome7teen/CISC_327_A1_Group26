def test_equipment_from_creates_item(client):
    response = client.post("/ui/equipment", data = {
        "name" : "Cordless Drill",
        "category" : "Tools",
        "total_units" : "3",
    })

    assert response.status_code == 302
    assert response.headers["Location"] == "/ui/equipment"

    items = client.get("/equipment").get_json()
    assert len(items) == 1
    assert items[0]["name"] == "Cordless Drill"
    assert items[0]["category"] == "Tools"
    assert items[0]["total_units"] == 3
    assert items[0]["available_units"] == 3

def test_equipment_delete_from_removes_only_selected_item(client):
    first = client.post("/equipment", json = {
        "name" : "Drill",
        "category" : "Climbing",
        "total_units" : 1,
    }).get_json()
    second = client.post("/equipment", json = {
        "name" : "Ladder",
        "category" : "Climbing",
        "total_units" : 1
    }).get_json()

    response = client.post(f"/ui/equipment/{first['id']}/delete")

    assert response.status_code == 302
    assert response.headers["Location"] == "/ui/equipment"

    remaining = client.get("/equipment").get_json()
    assert [item["id"] for item in remaining] == [second["id"]]
