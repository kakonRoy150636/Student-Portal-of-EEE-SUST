import os
from unittest.mock import Mock

import redis
from celery import Celery
from celery.beat import PersistentScheduler
from redis.exceptions import ConnectionError

from app.core.beat import RedisLease, SingletonScheduler, LOCK_KEY


def test_real_redis_allows_only_one_beat_publisher(monkeypatch, tmp_path):
    url = os.environ['INTEGRATION_REDIS_URL']
    store = redis.Redis.from_url(url)
    first_lease, second_lease = RedisLease(store), RedisLease(store)
    app = Celery('test-beat-lock', broker=url)
    tick = Mock(return_value=1)
    monkeypatch.setattr(PersistentScheduler, 'tick', tick)
    first = SingletonScheduler(app, lease=first_lease, schedule_filename=str(tmp_path/'first.db'))
    second = SingletonScheduler(app, lease=second_lease, schedule_filename=str(tmp_path/'second.db'))
    try:
        first.tick()
        second.tick()
        assert tick.call_count == 1
        assert store.ttl(LOCK_KEY) > 0
        second_lease.release()  # standby cannot delete the owner's lease
        assert store.get(LOCK_KEY).decode() == first_lease.owner
        first.close()
        second.tick()
        assert tick.call_count == 2
        assert store.get(LOCK_KEY).decode() == second_lease.owner
        store.set(LOCK_KEY, 'new-owner', ex=30)
        second.tick()
        assert tick.call_count == 2  # ownership loss prevents publication
    finally:
        first.close()
        second.close()
        store.delete(LOCK_KEY)
        store.close()


def test_beat_lease_fails_closed_during_redis_outage():
    client = Mock()
    client.set.side_effect = ConnectionError('unavailable')
    lease = RedisLease(client)
    assert lease.acquire_or_renew() is False
    client.eval.side_effect = ConnectionError('unavailable')
    assert lease.renew() is False
