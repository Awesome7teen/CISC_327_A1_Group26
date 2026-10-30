from datetime import date

import pytest


# Creates a renter through the API and returns the created record.
# Used as a helper to reduce duplicate setup code in tests.
def create_renter(client, name="Alex", email="alex@example.com"):
    response = client.post("/renters", json={
        "name": name,
        "email": email,
    })
    assert response.status_code == 201
    return response.get_json()


# Creates an equipment item through the API and returns the created record.
# Used by rental-related tests.
def create_equipment(client, name="Drill"):
    response = client.post("/equipment", json={
        "name": name,
        "category": "Tools",
        "total_units": 3,
    })
    assert response.status_code == 201
    return response.get_json()


# Creates a rental (equipment checkout) and returns the rental record.
# Allows tests to quickly set up rental scenarios.
def checkout(client, equipment, renter, deposit_amount=0):
    response = client.post("/rentals", json={
        "equipment_id": equipment["id"],
        "renter_id": renter["id"],
        "deposit_amount": deposit_amount,
    })
    assert response.status_code == 201
    return response.get_json()


# Retrieves a specific rental from the list endpoint.
# Useful for verifying that updates have been persisted.
def get_saved_rental(client, rental_id):
    records = client.get("/rentals").get_json()
    return next(record for record in records if record["id"] == rental_id)

#  Verifies that a newly created renter is stored correctly,
# including automatic generation of membership_date and ID.
def test_create_renter_saves_fields_and_membership_date(client):
    renter = create_renter(client)

    response = client.get(f"/renters/{renter['id']}")
    assert response.status_code == 200
    saved = response.get_json()

    assert saved["name"] == "Alex"
    assert saved["email"] == "alex@example.com"
    assert saved["membership_date"]
    assert saved["id"] == renter["id"]


# Ensures the renter listing endpoint returns all created renters.
def test_list_renters_contains_both_created_records(client):
    first = create_renter(client)
    second = create_renter(client, "Sam", "sam@example.com")

    response = client.get("/renters")
    assert response.status_code == 200
    records = response.get_json()

    assert {r["id"] for r in records} == {first["id"], second["id"]}
    assert {r["name"] for r in records} == {"Alex", "Sam"}


# Confirms renter updates are persisted while unrelated fields remain unchanged.
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


# Verifies that deleting a renter removes only that renter
# and leaves other renter records intact.
def test_delete_renter_removes_only_selected_record(client):
    first = create_renter(client)
    second = create_renter(client, "Sam", "sam@example.com")

    response = client.delete(f"/renters/{first['id']}")
    assert response.status_code == 204
    assert client.get(f"/renters/{first['id']}").status_code == 404

    remaining = client.get("/renters").get_json()
    assert [r["id"] for r in remaining] == [second["id"]]


# Ensures all renter operations return a 404 error
# when the specified renter does not exist.
@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_renter_returns_error(client, method):
    if method == "put":
        response = client.put("/renters/999", json={"name": "New"})
    else:
        response = getattr(client, method)("/renters/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Renter not found"}


# Verifies the rentals listing includes both active and returned rentals
# and preserves their correct status information.
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


# Confirms filtering rentals by renter returns only rentals
# that belong to the specified renter.
#
# Expected to fail because the current implementation compares
# equipment_id against renter_id instead of renter_id.
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


# Ensures filtering rentals by equipment returns only rentals
# associated with the selected equipment item.
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


# Verifies rental extensions correctly update the due date
# without affecting return status or equipment availability.
def test_extend_rental_saves_new_due_date(client):
    equipment = create_equipment(client)
    renter = create_renter(client)
    rental = checkout(client, equipment, renter)
    original_due_date = date.fromisoformat(rental["due_date"])

    response = client.put(
        f"/rentals/{rental['id']}/extend",
        json={"days": 3},
    )
    assert response.status_code == 200

    saved = get_saved_rental(client, rental["id"])
    new_due_date = date.fromisoformat(saved["due_date"])

    assert (new_due_date - original_due_date).days == 3
    assert saved["due_date"] == response.get_json()["due_date"]
    assert saved["return_date"] is None
    assert client.get(
        f"/equipment/{equipment['id']}"
    ).get_json()["available_units"] == 2


# Ensures a returned rental cannot be extended and that
# its original due date remains unchanged.
def test_returned_rental_cannot_be_extended(client):
    equipment = create_equipment(client)
    renter = create_renter(client)
    rental = checkout(client, equipment, renter)

    assert client.put(
        f"/rentals/{rental['id']}/return"
    ).status_code == 200

    response = client.put(
        f"/rentals/{rental['id']}/extend",
        json={"days": 3},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Rental already returned"}
    assert get_saved_rental(
        client, rental["id"]
    )["due_date"] == rental["due_date"]


# Verifies deposit release is recorded after a rental is returned.
#
# Expected to fail because the endpoint reports success but
# does not save the deposit_released flag.
def test_deposit_release_is_saved_after_return(client):
    """Expected to fail: release responds True but does not save the flag."""
    equipment = create_equipment(client)
    renter = create_renter(client)
    rental = checkout(client, equipment, renter, deposit_amount=50)

    assert client.put(
        f"/rentals/{rental['id']}/return"
    ).status_code == 200

    response = client.put(
        f"/rentals/{rental['id']}/deposit/release"
    )
    assert response.status_code == 200
    assert response.get_json() == {
        "rental_id": rental["id"],
        "deposit_released": True,
    }

    saved = get_saved_rental(client, rental["id"])
    assert saved["deposit_released"] is True
    assert saved["deposit_amount"] == 50


# Ensures deposits cannot be released until the equipment
# has been returned.
def test_deposit_cannot_be_released_before_return(client):
    equipment = create_equipment(client)
    renter = create_renter(client)
    rental = checkout(client, equipment, renter, deposit_amount=50)

    response = client.put(
        f"/rentals/{rental['id']}/deposit/release"
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Equipment has not been returned yet"
    }
    saved = get_saved_rental(client, rental["id"])
    assert saved["deposit_released"] is False
    assert saved["return_date"] is None


# Verifies rental-specific actions return a 404 error
# when the requested rental does not exist.
@pytest.mark.parametrize("suffix", ["extend", "deposit/release"])
def test_missing_rental_actions_return_error(client, suffix):
    response = client.put(
        f"/rentals/999/{suffix}", json={"days": 3}
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Rental not found"}