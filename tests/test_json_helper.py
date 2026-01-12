import json
from datetime import datetime
from utils.json_helpers import JsonEncoder


def test_json_encoder_handles_datetime_and_defaultdict():
    data = {
        'time': datetime(2020, 1, 2, 3, 4, 5),
        'nested': {'a': 1}
    }

    dumped = json.dumps(data, cls=JsonEncoder)
    loaded = json.loads(dumped)

    assert isinstance(loaded['time'], str)
    assert loaded['time'].startswith('2020-01-02T03:04:05')
    assert loaded['nested']['a'] == 1
