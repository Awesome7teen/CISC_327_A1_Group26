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

def test_renter_form_saves_name_and_email(client):
    response = client.post("/ui/renters", data = {
        "name" : "Sydney Kinnear",
        "email" : "sydney@example.com",
    })

    assert response.status_code == 302
    assert response.headers["Location"] == "/ui/renters"

    renters = client.get("/renters").get_json()
    assert len(renters) == 1
    assert renters[0]["name"] == "Sydney Kinnear"
    assert renters[0]["email"] == "sydney@example.com"

def test_renter_delete_form_removes_only_selected_renter(client):
    first = client.post("/renters", json = {
        "name" : "Sydney Kinnear",
        "email" : "sydney@example.com",
    })
    second = client.post("/renters", json = {
        "name" : "Nathan Diniro",
        "email" : "nathan@example.com",
    })
    assert first.status_code == second.status_code == 201

    renter_id = first.get_json()["id"]
    response = client.post(f"/ui/renters/{renter_id}/delete")

    assert response.status_code == 302
    assert response.headers["Location"] == "/ui/renters"

    remaining = client.get("/renters").get_json()
    assert [renter["id"] for renter in remaining] == [second.get_json()["id"]]