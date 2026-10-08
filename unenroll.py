import uuid
import time
import requests
import os
import device_management_backend_pb2 as proto

serial_number = input("serial number: ").strip()
oauth_code = input("oauth code: ").strip()

response = requests.post(
    "https://www.googleapis.com/oauth2/v4/token",
    data={
        "code": oauth_code,
        "client_id": "77185425430.apps.googleusercontent.com",
        "client_secret": "OTJgUOQcT7lO7GsGZq2G4IlT",
        "grant_type": "authorization_code",
    },
)

if not response.ok:
    exit("invalid or expired oauth code, please generate a new one")

refresh_token = response.json()["refresh_token"]

response = requests.post(
    "https://www.googleapis.com/oauth2/v4/token",
    data={
        "client_id": "77185425430.apps.googleusercontent.com",
        "client_secret": "OTJgUOQcT7lO7GsGZq2G4IlT",
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "https://www.googleapis.com/auth/chromeosdevicemanagement https://www.googleapis.com/auth/userinfo.email",
    },
)

response.raise_for_status()
oauth_token = response.json()["access_token"]

device_id = str(uuid.uuid4())

register_request = proto.DeviceRegisterRequest()
register_request.type = proto.DeviceRegisterRequest.DEVICE
register_request.machine_id = serial_number

request = proto.DeviceManagementRequest()
request.register_request.CopyFrom(register_request)

response = requests.post(
    f"https://m.google.com/devicemanagement/data/api?devicetype=2&apptype=Chrome&request=register&deviceid={device_id}&oauth_token={oauth_token}",
    headers={
        "Content-Type": "application/protobuf",
    },
    data=request.SerializeToString(),
)

data = proto.DeviceManagementResponse()
data.ParseFromString(response.content)

if data.error_message:
    exit(data.error_message)

dmtoken = data.register_response.device_management_token

policy_fetch_request = proto.PolicyFetchRequest()
policy_fetch_request.policy_type = "google/chromeos/device"

state_key_update_request = proto.DeviceStateKeyUpdateRequest()
for _ in range(5):
    state_key_update_request.server_backed_state_keys.append(os.urandom(32))

request = proto.DeviceManagementRequest()
request.policy_request.requests.append(policy_fetch_request)
request.device_state_key_update_request.CopyFrom(state_key_update_request)

requests.post(
    f"https://m.google.com/devicemanagement/data/api?retry=false&apptype=Chrome&deviceid={device_id}&devicetype=2&request=policy",
    headers={
        "Authorization": f"GoogleDMToken token={dmtoken}",
        "Content-Type": "application/protobuf",
    },
    data=request.SerializeToString(),
)