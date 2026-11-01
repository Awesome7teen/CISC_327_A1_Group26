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

def test_update_equipment_saves_changes(client):
    item = create_equipment(client)

    response = client.put(
        f"/equipment/{item['id']}",
        json={"name": "Cordless Drill", "category": "Power Tools"},
    )
    assert response.status_code == 200

    saved = client.get(f"/equipment/{item['id']}").get_json()

    assert saved["name"] == "Cordless Drill"
    assert saved["category"] == "Power Tools"
    assert saved["total_units"] == 2
    assert saved["available_units"] == 2


def test_delete_equipment_removes_only_selected_item(client):
    first = create_equipment(client, name="Drill")
    second = create_equipment(client, name="Ladder")

    response = client.delete(f"/equipment/{first['id']}")
    assert response.status_code == 204

    missing = client.get(f"/equipment/{first['id']}")
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "Equipment not found"}

    remaining = client.get("/equipment").get_json()
    assert len(remaining) == 1
    assert remaining[0]["id"] == second["id"]


def test_mark_equipment_out_of_service_and_restore(client):
    item = create_equipment(client)

    response = client.patch(
        f"/equipment/{item['id']}/status",
        json={"is_available": False},
    )
    assert response.status_code == 200

    saved = client.get(f"/equipment/{item['id']}").get_json()
    assert saved["is_available"] is False

    availability_response = client.get(
        f"/equipment/{item['id']}/availability"
    )
    assert availability_response.status_code == 200
    availability = availability_response.get_json()

    assert availability["equipment_id"] == item["id"]
    assert availability["is_available"] is False
    assert availability["total_units"] == 2
    assert availability["available_units"] == 2

    response = client.patch(
        f"/equipment/{item['id']}/status",
        json={"is_available": True},
    )
    assert response.status_code == 200

    restored = client.get(f"/equipment/{item['id']}").get_json()
    assert restored["is_available"] is True

    availability = client.get(
        f"/equipment/{item['id']}/availability"
    ).get_json()
    assert availability["is_available"] is True


def test_update_nonexistent_equipment_returns_error(client):
    response = client.put(
        "/equipment/999",
        json={"name": "Updated Drill"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}
    assert client.get("/equipment").get_json() == []


def test_delete_nonexistent_equipment_returns_error(client):
    response = client.delete("/equipment/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}
    assert client.get("/equipment").get_json() == []


def test_change_status_of_nonexistent_equipment_returns_error(client):
    response = client.patch(
        "/equipment/999/status",
        json={"is_available": False},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}


def test_check_availability_of_nonexistent_equipment_returns_error(client):
    response = client.get("/equipment/999/availability")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}


def create_renter(client):
    response = client.post("/renters", json={
        "name": "Test Renter",
        "email": "renter@example.com",
    })
    assert response.status_code == 201
    return response.get_json()


def test_checkout_records_rental_and_reduces_availability(client):
    item = create_equipment(client, total_units=2)
    renter = create_renter(client)

    response = client.post("/rentals", json={
        "equipment_id": item["id"],
        "renter_id": renter["id"],
    })

    assert response.status_code == 201
    rental = response.get_json()

    assert rental["equipment_id"] == item["id"]
    assert rental["renter_id"] == renter["id"]
    assert rental["rental_date"]
    assert rental["due_date"]
    assert rental["return_date"] is None

    records = client.get("/rentals").get_json()
    assert records == [rental]

    saved = client.get(f"/equipment/{item['id']}").get_json()
    assert saved["available_units"] == 1
    assert saved["total_units"] == 2


def test_checkout_nonexistent_equipment_creates_no_rental(client):
    renter = create_renter(client)

    response = client.post("/rentals", json={
        "equipment_id": 999,
        "renter_id": renter["id"],
    })

    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}
    assert client.get("/rentals").get_json() == []


def test_out_of_service_equipment_cannot_be_checked_out(client):
    item = create_equipment(client, total_units=2)
    renter = create_renter(client)

    status_response = client.patch(
        f"/equipment/{item['id']}/status",
        json={"is_available": False},
    )
    assert status_response.status_code == 200

    response = client.post("/rentals", json={
        "equipment_id": item["id"],
        "renter_id": renter["id"],
    })

    records = client.get("/rentals").get_json()
    saved = client.get(f"/equipment/{item['id']}").get_json()

    assert 400 <= response.status_code < 500
    assert records == []
    assert saved["available_units"] == 2


def test_return_records_date_and_restores_availability(client):
    item = create_equipment(client, total_units=1)
    renter = create_renter(client)

    checkout = client.post("/rentals", json={
        "equipment_id": item["id"],
        "renter_id": renter["id"],
    })
    assert checkout.status_code == 201
    rental_id = checkout.get_json()["id"]

    before_return = client.get(
        f"/equipment/{item['id']}"
    ).get_json()
    assert before_return["available_units"] == 0

    response = client.put(f"/rentals/{rental_id}/return")
    assert response.status_code == 200
    returned = response.get_json()
    assert returned["return_date"] is not None

    saved_rental = client.get("/rentals").get_json()[0]
    assert saved_rental["return_date"] == returned["return_date"]

    saved_item = client.get(f"/equipment/{item['id']}").get_json()
    assert saved_item["available_units"] == 1


def test_repeated_return_does_not_increase_availability_twice(client):
    item = create_equipment(client, total_units=1)
    renter = create_renter(client)

    checkout = client.post("/rentals", json={
        "equipment_id": item["id"],
        "renter_id": renter["id"],
    })
    assert checkout.status_code == 201
    rental_id = checkout.get_json()["id"]

    first_return = client.put(f"/rentals/{rental_id}/return")
    assert first_return.status_code == 200

    second_return = client.put(f"/rentals/{rental_id}/return")
    assert second_return.status_code == 400
    assert second_return.get_json() == {
        "error": "Rental already returned"
    }

    saved = client.get(f"/equipment/{item['id']}").get_json()
    assert saved["available_units"] == 1

    saved_rental = client.get("/rentals").get_json()[0]
    assert saved_rental["return_date"] == (
        first_return.get_json()["return_date"]
    )


def test_return_nonexistent_rental_returns_error(client):
    response = client.put("/rentals/999/return")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Rental not found"}
    assert client.get("/rentals").get_json() == []