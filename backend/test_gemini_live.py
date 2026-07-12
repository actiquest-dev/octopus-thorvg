#!/usr/bin/env python3
"""
Test script to verify Gemini Live API connectivity
"""
import os
import json
import asyncio
import websockets
from google.oauth2 import service_account
from google.auth.transport.requests import Request

async def test_gemini_live():
    print("=" * 60)
    print("🧪 Testing Gemini Live API Connection")
    print("=" * 60)

    # Step 1: Load credentials
    print("\n1️⃣ Loading credentials...")
    creds_path = "/Users/miguelaprossine/octopus-thorvg/credentials.json"

    if not os.path.exists(creds_path):
        print(f"❌ Credentials file not found: {creds_path}")
        return False

    try:
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)
        print(f"✅ Credentials loaded")
        print(f"   Project ID: {creds_data.get('project_id')}")
        print(f"   Service Account: {creds_data.get('client_email')}")
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return False

    # Step 2: Generate Bearer token
    print("\n2️⃣ Generating Bearer token...")
    try:
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        creds.refresh(Request())
        token = creds.token
        print(f"✅ Bearer token generated")
        print(f"   Token (first 50 chars): {token[:50]}...")
        print(f"   Project: {creds.project_id}")
    except Exception as e:
        print(f"❌ Failed to generate token: {e}")
        return False

    # Step 3: Build WebSocket URL
    print("\n3️⃣ Building WebSocket URL...")
    project_id = creds_data.get('project_id')
    location = "us-central1"
    model = "gemini-live-2.5-flash-native-audio"

    service_url = f"wss://{location}-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent"
    print(f"✅ WebSocket URL: {service_url}")

    # Step 4: Try to connect
    print("\n4️⃣ Attempting WebSocket connection...")
    try:
        async with websockets.connect(
            service_url,
            additional_headers=[
                ("Authorization", f"Bearer {token}"),
                ("Content-Type", "application/json"),
            ],
            ping_interval=20,
            ping_timeout=20,
            close_timeout=1,
        ) as websocket:
            print("✅ WebSocket connected successfully!")

            # Step 5: Send setup message
            print("\n5️⃣ Sending setup message...")
            setup_msg = {
                "setup": {
                    "model": f"projects/{project_id}/locations/{location}/publishers/google/models/{model}",
                    "generation_config": {
                        "response_modalities": ["AUDIO"],
                        "temperature": 1.0,
                    },
                    "system_instruction": {"parts": [{"text": "You are a helpful assistant."}]},
                    "input_audio_transcription": {},
                    "output_audio_transcription": {}
                }
            }

            await websocket.send(json.dumps(setup_msg))
            print("✅ Setup message sent")

            # Step 6: Wait for response
            print("\n6️⃣ Waiting for setup complete response...")
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)

            if response_data.get('setupComplete'):
                print("✅ Setup complete!")
                print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
            else:
                print(f"⚠️ Received response (not setupComplete):")
                print(f"   {json.dumps(response_data, indent=2)[:200]}...")

            return True

    except asyncio.TimeoutError:
        print("❌ Timeout waiting for setup response")
        return False
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    result = await test_gemini_live()

    print("\n" + "=" * 60)
    if result:
        print("✅ ALL TESTS PASSED - Gemini Live is accessible!")
    else:
        print("❌ TESTS FAILED - Check the errors above")
    print("=" * 60)

    return 0 if result else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
