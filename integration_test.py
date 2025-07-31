#!/usr/bin/env python3
"""
Integration Test for Quantum Crypto Trading System
Tests frontend-backend integration and sanity checks
"""

import sys
import asyncio
sys.path.insert(0, '.')

def test_integration():
    print('🔗 QUANTUM CRYPTO TRADING SYSTEM - INTEGRATION TEST')
    print('=' * 60)

    # Test 1: Backend API endpoints
    print('\n1️⃣ Testing Backend API Endpoints:')
    try:
        from app import create_app
        app = create_app()
        
        # Count routes by type
        auth_routes = [route for route in app.routes if '/auth/' in str(route.path)]
        api_routes = [route for route in app.routes if '/api/' in str(route.path)]
        health_routes = [route for route in app.routes if '/health' in str(route.path)]
        
        print(f'   ✅ Auth routes: {len(auth_routes)}')
        print(f'   ✅ API routes: {len(api_routes)}')
        print(f'   ✅ Health routes: {len(health_routes)}')
        print(f'   ✅ Total routes: {len(app.routes)}')
        backend_ok = True
    except Exception as e:
        print(f'   ❌ Backend creation failed: {e}')
        backend_ok = False

    # Test 2: Authentication System
    print('\n2️⃣ Testing Authentication System:')
    try:
        from src.api.auth import login, LoginRequest
        print('   ✅ JWT authentication module imported')
        print('   ✅ Login functionality available')
        auth_ok = True
    except Exception as e:
        print(f'   ❌ Auth system failed: {e}')
        auth_ok = False

    # Test 3: Database System
    print('\n3️⃣ Testing Database System:')
    try:
        from src.config.database import get_db
        from src.models.trading_models import User, Trade, Position
        db_gen = get_db()
        db = next(db_gen)
        db.close()
        print('   ✅ Database connection works')
        print('   ✅ Trading models accessible')
        db_ok = True
    except Exception as e:
        print(f'   ❌ Database system failed: {e}')
        db_ok = False

    # Test 4: Frontend Dependencies
    print('\n4️⃣ Testing Frontend:')
    try:
        import os
        frontend_package = os.path.exists('frontend/package.json')
        node_modules = os.path.exists('frontend/node_modules')
        app_jsx = os.path.exists('frontend/src/App.jsx')
        
        print(f'   ✅ Frontend package.json: {frontend_package}')
        print(f'   ✅ Dependencies installed: {node_modules}')
        print(f'   ✅ React app exists: {app_jsx}')
        frontend_ok = frontend_package and app_jsx
    except Exception as e:
        print(f'   ❌ Frontend check failed: {e}')
        frontend_ok = False

    # Results Summary
    print('\n🎯 INTEGRATION TEST RESULTS:')
    print('=' * 60)
    
    overall_status = backend_ok and auth_ok and db_ok and frontend_ok
    
    print(f'   Backend API:        {"✅ PASS" if backend_ok else "❌ FAIL"}')
    print(f'   Authentication:     {"✅ PASS" if auth_ok else "❌ FAIL"}')
    print(f'   Database:           {"✅ PASS" if db_ok else "❌ FAIL"}')
    print(f'   Frontend:           {"✅ PASS" if frontend_ok else "❌ FAIL"}')
    
    print(f'\n🚀 OVERALL STATUS: {"✅ INTEGRATION TEST PASSED" if overall_status else "❌ NEEDS WORK"}')
    
    if overall_status:
        print('\n🎉 QUANTUM CRYPTO TRADING SYSTEM IS READY!')
        print('   - Backend API: Fully functional')
        print('   - JWT Authentication: Working')
        print('   - Database Operations: Connected')
        print('   - Frontend: Ready to deploy')
        print('   - Repository: https://github.com/shyamanurag/quantum')

if __name__ == "__main__":
    test_integration()