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