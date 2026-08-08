#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test chat tool with proper UTF-8 encoding"""
import requests
import json

url = "http://localhost:8080/jsonrpc"

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "chat",
        "arguments": {
            "message": "你好"
        }
    }
}

headers = {
    "Content-Type": "application/json; charset=utf-8"
}

response = requests.post(url, json=payload, headers=headers)

print("Status Code:", response.status_code)

# Save to file to avoid Windows GBK encoding issues
with open("test_response.json", "w", encoding="utf-8") as f:
    json.dump(response.json(), f, indent=2, ensure_ascii=False)

print("\nResponse saved to: test_response.json")
print("Preview (ASCII-safe):")
print(json.dumps(response.json(), indent=2, ensure_ascii=True))
