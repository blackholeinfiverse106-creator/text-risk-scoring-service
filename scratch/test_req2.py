import json
import requests
import uuid
trace_id = f"prop-{uuid.uuid4()}"
token = {"execution_id": trace_id, "rajya_verdict": "EXECUTION_APPROVED", "timestamp": "2026-07-28T09:58:00.123456+00:00", "token_status": "ACTIVE", "signature_hash": "a6e7c41fbed1aafbc64fe843f2f1e4b934cb0118bed23ad0d1d98beb6e73285e"}
payload = {'input': 'Test', 'agent': 'core-agent', 'trace_id': trace_id, 'task_id': 'task-123', 'execution_token': json.dumps(token)}
r = requests.post('http://163.128.209.18:8004/execute_task', json=payload)
print(r.status_code)
print(r.text)
