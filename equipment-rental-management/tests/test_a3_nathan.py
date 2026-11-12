
from datetime import date, timedelta
from unittest.mock import patch

from app import store
from app.models.rental import Rental
from app.models.renter import Renter


def setup_rental():
    """Create a renter and rental for notification tests."""

    store.reset()

    renter = Renter(
        id=1,
        name="John Smith",
        email="john@example.com"
    )

    rental = Rental(
        id=1,
        equipment_id=1,
        renter_id=1,
        due_date=date.today() + timedelta(days=1)
    )

    store.renters[1] = renter
    store.rentals[1] = rental

    # The reminder endpoint checks that the equipment exists.
    # It doesn't need any equipment attributes.
    store.equipment[1] = object()



def test_return_reminder_success(client, monkeypatch):
    setup_rental()

    # Replace the real notification service with a stub.
    def fake_send_notification(recipient, subject, message):
        return True

    monkeypatch.setattr(
        "app.routes.rentals.send_notification",
        fake_send_notification
    )

    response = client.post("/rentals/1/remind")

    assert response.status_code == 200
    assert response.get_json()["notification_sent"] is True


def test_return_reminder_correct_notification_details(client):
    setup_rental()

    with patch(
        "app.routes.rentals.send_notification",
        return_value=True
    ) as mock_notification:

        response = client.post("/rentals/1/remind")

        assert response.status_code == 200

        mock_notification.assert_called_once_with(
            "john@example.com",
            "Upcoming Equipment Return Reminder",
            (
                "Hello John Smith, your rental for "
                "equipment ID 1 is due on "
                f"{(date.today() + timedelta(days=1)).isoformat()}. "
                "Please return it on time to avoid late fees."
            )
        )

    assert response.get_json()["notification_sent"] is True
