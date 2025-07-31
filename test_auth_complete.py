#!/usr/bin/env python3
"""
Comprehensive authentication test for the trading system
"""
import requests
import json
import sys

API_BASE = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE}/health")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"System: {health_data.get('system')}")
            print(f"Status: {health_data.get('status')}")
            print(f"Orchestrator Initialized: {health_data.get('checks', {}).get('orchestrator_initialized')}")
            print(f"Orchestrator Running: {health_data.get('checks', {}).get('orchestrator_running')}")
            return True
        else:
            print(f"❌ Health check failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_trades():
    """Test trades endpoint"""
    print("\n📊 Testing trades endpoint...")
    try:
        response = requests.get(f"{API_BASE}/api/trades/")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            trades = response.json()
            print(f"Trades count: {len(trades)}")
            print(f"Response: {trades}")
            return True
        else:
            print(f"❌ Trades failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Trades error: {e}")
        return False

def test_auth_login():
    """Test authentication login"""
    print("\n🔐 Testing authentication...")
    try:
        # Test login
        login_data = {"username": "admin", "password": "admin123"}
        response = requests.post(
            f"{API_BASE}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Login Status: {response.status_code}")
        
        if response.status_code == 200:
            auth_result = response.json()
            token = auth_result.get('access_token')
            if token:
                print(f"✅ Login successful! Token received")
                print(f"User: {auth_result.get('username')}")
                print(f"Role: {auth_result.get('role')}")
                return token
            else:
                print(f"❌ No token in response: {auth_result}")
                return None
        else:
            print(f"❌ Login failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return None

def test_authenticated_request(token):
    """Test authenticated request"""
    print("\n🔒 Testing authenticated request...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_BASE}/api/auth/me", headers=headers)
        print(f"Auth verification status: {response.status_code}")
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Authenticated request successful!")
            print(f"User info: {user_info}")
            return True
        else:
            print(f"❌ Authenticated request failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Authenticated request error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting comprehensive system test...\n")
    
    results = {}
    
    # Test health
    results['health'] = test_health()
    
    # Test trades
    results['trades'] = test_trades()
    
    # Test authentication
    token = test_auth_login()
    results['auth_login'] = token is not None
    
    if token:
        results['auth_verify'] = test_authenticated_request(token)
    else:
        results['auth_verify'] = False
    
    # Summary
    print("\n" + "="*50)
    print("📋 TEST RESULTS SUMMARY:")
    print("="*50)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.upper():15}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 ALL TESTS PASSED - System is functional!")
        return 0
    else:
        print("⚠️ Some tests failed - System needs attention")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 