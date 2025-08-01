# 🔍 MONITORING COMMANDS - Deployment Verification

**Use these commands to verify deployment success:**

---

## 📊 **IMMEDIATE VERIFICATION (Now)**

### **Check Digital Ocean Status:**
```bash
# Go to: https://cloud.digitalocean.com/apps
# Look for: quantum-crypto-trading app
# Status should show: "Deploying" → "Live"
```

### **Test Health Endpoint:**
```bash
curl https://quantum-qwhjm.ondigitalocean.app/health
# Expected: {"status": "healthy"}
```

### **Test API Status:**
```bash
curl https://quantum-qwhjm.ondigitalocean.app/api/status
# Expected: JSON response with system status
```

---

## 🔍 **LOG MONITORING (5-10 minutes)**

### **Check for Success Indicators:**
```
✅ "Starting gunicorn 21.2.0"
✅ "Listening at: http://0.0.0.0:8000"
✅ "Booting worker with pid: X" (2 workers)
✅ "Redis configured for: cachequantum..."
✅ "PostgreSQL database configured"
✅ No IndentationError messages
✅ No component restart loops
```

### **Check for Failure Indicators:**
```
❌ "IndentationError: unexpected indent"
❌ "Worker failed to boot"
❌ "connection refused"
❌ "component terminated with non-zero exit code"
❌ "ERROR component quantum exited with code: 1"
```

---

## 🎯 **FUNCTIONAL TESTING**

### **Position Management API:**
```bash
curl https://quantum-qwhjm.ondigitalocean.app/api/position-management/
# Expected: Position data (not 500 error)
```

### **Order Management API:**
```bash
curl https://quantum-qwhjm.ondigitalocean.app/api/order-management/
# Expected: Order system status
```

### **Arbitrage Status (Should be Clean):**
```bash
curl https://quantum-qwhjm.ondigitalocean.app/api/arbitrage/opportunities
# Expected: Clean response, no fake profit spam
```

---

## 📈 **SUCCESS CONFIRMATION**

### **All Green Indicators:**
- ✅ Health checks passing
- ✅ Workers stable (no crashes)
- ✅ APIs responding
- ✅ No restart loops
- ✅ Professional log output

### **Performance Metrics:**
- 🎯 Response time: < 2 seconds
- 🎯 Memory usage: Within basic-xs limits
- 🎯 CPU usage: Stable
- 🎯 Error rate: Zero

---

## 🚨 **IF ISSUES PERSIST**

### **Common Remaining Issues:**
1. **Import errors** (other than web3/tensorflow/tweepy)
2. **Database connection failures**
3. **Memory constraints on basic-xs**
4. **New syntax errors in other files**

### **Immediate Actions:**
1. Check Digital Ocean build logs
2. Verify environment variables
3. Test individual API endpoints
4. Review specific error messages

---

**🎯 GOAL: Confirm all 7 critical issues are resolved and system is stable!**