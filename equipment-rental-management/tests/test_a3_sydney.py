from datetime import date, timedelta
from unittest.mock import patch
from app import store

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

def create_rental_for_reminder(client, due_in_days):
    equipment = client.post("/equipment", json = {
        "name": "Drill",
        "category": "Tools",
        "total_units": 1,
    })
    assert equipment.status_code == 201

    renter = client.post("/renters", json = {
        "name" : "Sydney Kinnear",
        "email" : "sydney@example.com",
    })
    assert renter.status_code == 201

    rental = client.post("/rentals", json = {
        "equipment_id" : equipment.get_json()["id"],
        "renter_id" : renter.get_json()["id"],
    })
    assert rental.status_code == 201

    rental_id = rental.get_json()["id"]
    store.rentals[rental_id].due_date = date.today() + timedelta(days = due_in_days)
    return rental_id

def test_return_reminder_reports_notification_failure(client, monkeypatch):
    rental_id = create_rental_for_reminder(client, due_in_days = 1)
    rentals_before = client.get("/rentals").get_json()

    monkeypatch.setattr(
        "app.routes.rentals.send_notification",
        lambda recipiant, subject, message: False,
    )

    response = client.post(f"/rentals/{rental_id}/remind")

    assert response.status_code == 200
    assert response.get_json() == {
        "message" : "Return reminder processed",
        "notification_sent" : False,
    }
    assert client.get("/rentals").get_json() == rentals_before

def test_return_reminder_skips_notification_when_not_due(client):
    rental_id = create_rental_for_reminder(client, due_in_days = 2)
    rentals_before = client.get("/rentals").get_json()

    with patch("app.routes.rentals.send_notification") as send_notification:
        response = client.post(f"/rentals/{rental_id}/remind")
        send_notification.assert_not_called()

    assert response.status_code == 400
    assert response.get_json() == {"error": "Reminder is not due yet"}
    assert client.get("/rentals").get_json() == rentals_before