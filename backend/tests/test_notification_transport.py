from unittest.mock import Mock

import pytest

from app.integrations import firebase_client as transport


@pytest.mark.parametrize('kind,expected', [
    ('unregistered', transport.InvalidDeviceToken),
    ('quota', transport.RetryableFCMError),
    ('unavailable', transport.RetryableFCMError),
    ('deadline', transport.AmbiguousFCMError),
    ('invalid_payload', transport.PermanentFCMError),
])
def test_fcm_provider_error_classification(monkeypatch, kind, expected):
    from firebase_admin import messaging, exceptions
    errors = {
        'unregistered': messaging.UnregisteredError('do-not-log-token-or-response'),
        'quota': messaging.QuotaExceededError('do-not-log-token-or-response'),
        'unavailable': exceptions.UnavailableError('do-not-log-token-or-response'),
        'deadline': exceptions.DeadlineExceededError('do-not-log-token-or-response'),
        'invalid_payload': exceptions.InvalidArgumentError('do-not-log-token-or-response'),
    }
    monkeypatch.setattr(transport, '_get_app', lambda *args: object())
    monkeypatch.setattr(messaging, 'send', Mock(side_effect=errors[kind]))
    with pytest.raises(expected) as caught:
        transport.dispatch_push_notification('secret-device-token', 'Portal update', 'Open the portal.')
    assert 'secret-device' not in str(caught.value)
    assert 'do-not-log' not in str(caught.value)


def test_fcm_high_and_normal_priorities(monkeypatch):
    from firebase_admin import messaging
    monkeypatch.setattr(transport, '_get_app', lambda *args: object())
    send = Mock(return_value='projects/test/messages/id')
    monkeypatch.setattr(messaging, 'send', send)
    for priority, apns in [('high', '10'), ('normal', '5')]:
        assert transport.dispatch_push_notification('token', 'Update', 'Open portal', priority=priority)
        message = send.call_args.args[0]
        assert message.android.priority == priority
        assert message.webpush.headers['Urgency'] == priority
        assert message.apns.headers['apns-priority'] == apns


def test_fcm_explicit_invalid_token_field(monkeypatch):
    from firebase_admin import messaging, exceptions
    response = Mock()
    response.json.return_value = {'error':{'details':[{
        '@type':'type.googleapis.com/google.rpc.BadRequest',
        'fieldViolations':[{'field':'message.token'}],
    }]}}
    error = exceptions.InvalidArgumentError('invalid', http_response=response)
    monkeypatch.setattr(transport, '_get_app', lambda *args: object())
    monkeypatch.setattr(messaging, 'send', Mock(side_effect=error))
    with pytest.raises(transport.InvalidDeviceToken):
        transport.dispatch_push_notification('invalid-token', 'Update', 'Open portal')


def test_fcm_initialization_disables_hidden_transport_retries(monkeypatch):
    from firebase_admin import messaging
    from requests import Session
    app = object()
    admin = Mock()
    admin.get_app.return_value = app
    service = Mock()
    service._client.session = Session()
    monkeypatch.setattr(messaging, '_get_messaging_service', Mock(return_value=service))
    monkeypatch.setattr(transport, '_configured_app', None)
    assert transport._get_app(admin, Mock(), messaging) is app
    assert service._client._timeout == 10
    assert service._client.session.get_adapter('https://fcm.googleapis.com').max_retries.total == 0
    transport._get_app(admin, Mock(), messaging)
    messaging._get_messaging_service.assert_called_once()


def test_celery_delivery_autoretry_uses_exponential_countdown(monkeypatch):
    from app.tasks import notifications as tasks
    from celery.exceptions import Retry
    async def fail(sessions, ident):
        raise transport.RetryableFCMError('temporary')
    async def with_sessions(callback):
        return await callback(None)
    monkeypatch.setattr(tasks, 'deliver_batch', fail)
    monkeypatch.setattr(tasks, '_with_sessions', with_sessions)
    retry = Mock(side_effect=Retry())
    monkeypatch.setattr(tasks.deliver_notification, 'retry', retry)
    for attempts, countdown in [(0, 60), (1, 120), (2, 240)]:
        tasks.deliver_notification.push_request(retries=attempts)
        try:
            with pytest.raises(Retry):
                tasks.deliver_notification.run('00000000-0000-0000-0000-000000000001')
            assert retry.call_args.kwargs['countdown'] == countdown
        finally:
            tasks.deliver_notification.pop_request()


def test_celery_dhaka_schedule():
    from app.core.celery_app import celery_app
    assert celery_app.conf.timezone == 'Asia/Dhaka'
    assert celery_app.conf.enable_utc is True
    schedule = celery_app.conf.beat_schedule
    assert len(schedule['scan-10-minute-class-alerts']['schedule'].minute) == 60
    assert schedule['medium-notification-digest']['schedule'].minute == set(range(0,60,5))
