from celery import Celery
import os

REDIS = os.getenv('REDIS_URL', 'redis://localhost:6379/0')


def make_celery(name='webapp'):
    return Celery(name, broker=REDIS, backend=REDIS)
