from datetime import date

import pytest


def create_renter(client, name="Alex", email="alex@example.com"):
    response = client.post("/renters", json={
        "name": name,
        "email": email,
    })
    assert response.status_code == 201
    return response.get_json()


def create_equipment(client, name="Drill"):
    response = client.post("/equipment", json={
        "name": name,
        "category": "Tools",
        "total_units": 3,
    })
    assert response.status_code == 201
    return response.get_json()


def checkout(client, equipment, renter, deposit_amount=0):
    response = client.post("/rentals", json={
        "equipment_id": equipment["id"],
        "renter_id": renter["id"],
        "deposit_amount": deposit_amount,
    })
    assert response.status_code == 201
    return response.get_json()


def get_saved_rental(client, rental_id):
    records = client.get("/rentals").get_json()
    return next(record for record in records if record["id"] == rental_id)

def test_create_renter_saves_fields_and_membership_date(client):
    renter = create_renter(client)

    response = client.get(f"/renters/{renter['id']}")
    assert response.status_code == 200
    saved = response.get_json()

    assert saved["name"] == "Alex"
    assert saved["email"] == "alex@example.com"
    assert saved["membership_date"]
    assert saved["id"] == renter["id"]


def test_list_renters_contains_both_created_records(client):
    first = create_renter(client)
    second = create_renter(client, "Sam", "sam@example.com")

    response = client.get("/renters")
    assert response.status_code == 200
    records = response.get_json()

    assert {r["id"] for r in records} == {first["id"], second["id"]}
    assert {r["name"] for r in records} == {"Alex", "Sam"}


def test_update_renter_persists_and_preserves_other_fields(client):
    renter = create_renter(client)

    response = client.put(
        f"/renters/{renter['id']}",
        json={"email": "new@example.com"},
    )
    assert response.status_code == 200

    saved = client.get(f"/renters/{renter['id']}").get_json()
    assert saved["email"] == "new@example.com"
    assert saved["name"] == renter["name"]
    assert saved["membership_date"] == renter["membership_date"]


def test_delete_renter_removes_only_selected_record(client):
    first = create_renter(client)
    second = create_renter(client, "Sam", "sam@example.com")

    response = client.delete(f"/renters/{first['id']}")
    assert response.status_code == 204
    assert client.get(f"/renters/{first['id']}").status_code == 404

    remaining = client.get("/renters").get_json()
    assert [r["id"] for r in remaining] == [second["id"]]


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_renter_returns_error(client, method):
    if method == "put":
        response = client.put("/renters/999", json={"name": "New"})
    else:
        response = getattr(client, method)("/renters/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Renter not found"}
    

def test_list_rentals_preserves_active_and_returned_records(client):
    equipment = create_equipment(client)
    renter = create_renter(client)

    first = checkout(client, equipment, renter)
    second = checkout(client, equipment, renter)

    returned = client.put(f"/rentals/{first['id']}/return")
    assert returned.status_code == 200

    response = client.get("/rentals")
    assert response.status_code == 200
    records = {r["id"]: r for r in response.get_json()}

    assert set(records) == {first["id"], second["id"]}
    assert records[first["id"]]["return_date"] is not None
    assert records[second["id"]]["return_date"] is None
    assert all(r["equipment_id"] == equipment["id"]
               for r in records.values())
    assert all(r["renter_id"] == renter["id"]
               for r in records.values())


def test_filter_rentals_by_renter_returns_only_that_renters_records(client):
    """Expected to fail: the route compares equipment_id to renter_id."""
    first_renter = create_renter(client)
    second_renter = create_renter(client, "Sam", "sam@example.com")
    equipment = create_equipment(client)

    # Cross the IDs so a mistaken equipment-ID filter cannot pass by chance.
    expected = checkout(client, equipment, second_renter)
    checkout(client, equipment, first_renter)

    response = client.get(
        "/rentals",
        query_string={"renter_id": second_renter["id"]},
    )

    assert response.status_code == 200
    records = response.get_json()
    assert [r["id"] for r in records] == [expected["id"]]
    assert all(r["renter_id"] == second_renter["id"] for r in records)


def test_filter_rentals_by_equipment_excludes_other_equipment(client):
    first = create_equipment(client, "Drill")
    second = create_equipment(client, "Ladder")
    renter = create_renter(client)

    expected = checkout(client, first, renter)
    checkout(client, second, renter)

    response = client.get(
        "/rentals",
        query_string={"equipment_id": first["id"]},
    )

    assert response.status_code == 200
    records = response.get_json()
    assert [r["id"] for r in records] == [expected["id"]]
    assert all(r["equipment_id"] == first["id"] for r in records)