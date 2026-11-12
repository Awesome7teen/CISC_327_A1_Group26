
from datetime import date, timedelta

from app import store
from app.models.equipment import Equipment
from app.models.renter import Renter
from app.models.rental import Rental


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200


def test_equipment_page_get(client):
    response = client.get("/ui/equipment")
    assert response.status_code == 200


def test_create_equipment(client):
    response = client.post(
        "/ui/equipment",
        data={
            "name": "Drill",
            "category": "Tools",
            "total_units": "5",
        },
    )

    assert response.status_code == 302
    assert len(store.equipment) == 1

    item = store.equipment[1]
    assert item.name == "Drill"
    assert item.category == "Tools"
    assert item.total_units == 5
    assert item.available_units == 5


def test_delete_equipment(client):
    item = Equipment(
        id=1,
        name="Drill",
        category="Tools",
        total_units=5,
        available_units=5,
    )
    store.equipment[1] = item

    response = client.post("/ui/equipment/1/delete")

    assert response.status_code == 302
    assert 1 not in store.equipment


def test_renters_page_get(client):
    response = client.get("/ui/renters")
    assert response.status_code == 200


def test_create_renter(client):
    response = client.post(
        "/ui/renters",
        data={
            "name": "John Smith",
            "email": "john@example.com",
        },
    )

    assert response.status_code == 302
    assert len(store.renters) == 1
    assert store.renters[1].name == "John Smith"
    assert store.renters[1].email == "john@example.com"


def test_delete_renter(client):
    store.renters[1] = Renter(
        id=1,
        name="John Smith",
        email="john@example.com",
    )

    response = client.post("/ui/renters/1/delete")

    assert response.status_code == 302
    assert 1 not in store.renters


def test_rentals_page_get(client):
    response = client.get("/ui/rentals")
    assert response.status_code == 200


def test_create_rental(client):
    item = Equipment(
        id=1,
        name="Drill",
        category="Tools",
        total_units=5,
        available_units=5,
    )
    store.equipment[1] = item

    store.renters[1] = Renter(
        id=1,
        name="John Smith",
        email="john@example.com",
    )

    response = client.post(
        "/ui/rentals",
        data={
            "equipment_id": "1",
            "renter_id": "1",
        },
    )

    assert response.status_code == 302
    assert len(store.rentals) == 1
    assert store.rentals[1].equipment_id == 1
    assert store.rentals[1].renter_id == 1
    assert item.available_units == 4


def test_rental_with_unavailable_equipment(client):
    item = Equipment(
        id=1,
        name="Drill",
        category="Tools",
        total_units=5,
        available_units=0,
    )
    store.equipment[1] = item

    response = client.post(
        "/ui/rentals",
        data={
            "equipment_id": "1",
            "renter_id": "1",
        },
    )

    assert response.status_code == 400
    assert response.get_data(as_text=True) == "Equipment is out of service"
    assert len(store.rentals) == 0
    assert item.available_units == 0