#!/bin/bash
# Smoke test script for ZAND deposit simulation endpoint
# Usage: TOKEN="your-jwt-token" ./scripts/smoke_deposit_sim.sh

set -e

API_BASE="${API_BASE:-http://localhost:8000}"
ENDPOINT="${API_BASE}/api/v1/webhooks/zandbank/simulate"
WALLET_ENDPOINT="${API_BASE}/api/v1/wallet?currency=AED"
AMOUNT="${AMOUNT:-10.00}"
REFERENCE="${REFERENCE:-ZAND-SMOKE-$(date +%s)}"

if [ -z "$TOKEN" ]; then
    echo "ERROR: TOKEN environment variable is required"
    echo "Usage: TOKEN='your-jwt-token' $0"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════"
echo "ZAND Deposit Simulation Smoke Test"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Step 1: Get initial wallet balance
echo "1. Fetching initial wallet balance..."
INITIAL_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$WALLET_ENDPOINT")

HTTP_CODE=$(echo "$INITIAL_RESPONSE" | tail -n1)
INITIAL_BODY=$(echo "$INITIAL_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: Failed to fetch initial wallet (HTTP $HTTP_CODE)"
    echo "$INITIAL_BODY" | jq '.' 2>/dev/null || echo "$INITIAL_BODY"
    exit 1
fi

INITIAL_TOTAL=$(echo "$INITIAL_BODY" | jq -r '.total_balance // "0.00"')
INITIAL_BLOCKED=$(echo "$INITIAL_BODY" | jq -r '.blocked_balance // "0.00"')

echo "   Initial Total Balance: $INITIAL_TOTAL AED"
echo "   Initial Blocked Balance: $INITIAL_BLOCKED AED"
echo ""

# Step 2: Simulate deposit
echo "2. Simulating deposit of $AMOUNT AED..."
DEPOSIT_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"currency\":\"AED\",\"amount\":\"$AMOUNT\",\"reference\":\"$REFERENCE\"}" \
    "$ENDPOINT")

HTTP_CODE=$(echo "$DEPOSIT_RESPONSE" | tail -n1)
DEPOSIT_BODY=$(echo "$DEPOSIT_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: Deposit simulation failed (HTTP $HTTP_CODE)"
    echo "$DEPOSIT_BODY" | jq '.' 2>/dev/null || echo "$DEPOSIT_BODY"
    exit 1
fi

echo "$DEPOSIT_BODY" | jq '.'
OPERATION_ID=$(echo "$DEPOSIT_BODY" | jq -r '.operation_id')
SIM_VERSION=$(echo "$DEPOSIT_BODY" | jq -r '.sim_version // "N/A"')

if [ -z "$OPERATION_ID" ] || [ "$OPERATION_ID" == "null" ]; then
    echo "ERROR: operation_id missing in response"
    exit 1
fi

echo "   ✓ Operation ID: $OPERATION_ID"
echo "   ✓ Sim Version: $SIM_VERSION"
echo ""

# Step 3: Verify wallet balance increased
echo "3. Verifying wallet balance updated..."
sleep 1  # Small delay to ensure DB commit

FINAL_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$WALLET_ENDPOINT")

HTTP_CODE=$(echo "$FINAL_RESPONSE" | tail -n1)
FINAL_BODY=$(echo "$FINAL_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: Failed to fetch final wallet (HTTP $HTTP_CODE)"
    echo "$FINAL_BODY" | jq '.' 2>/dev/null || echo "$FINAL_BODY"
    exit 1
fi

FINAL_TOTAL=$(echo "$FINAL_BODY" | jq -r '.total_balance // "0.00"')
FINAL_BLOCKED=$(echo "$FINAL_BODY" | jq -r '.blocked_balance // "0.00"')

echo "   Final Total Balance: $FINAL_TOTAL AED"
echo "   Final Blocked Balance: $FINAL_BLOCKED AED"
echo ""

# Step 4: Verify balance increased correctly
INITIAL_TOTAL_NUM=$(echo "$INITIAL_TOTAL" | sed 's/[^0-9.]//g')
FINAL_TOTAL_NUM=$(echo "$FINAL_TOTAL" | sed 's/[^0-9.]//g')
INITIAL_BLOCKED_NUM=$(echo "$INITIAL_BLOCKED" | sed 's/[^0-9.]//g')
FINAL_BLOCKED_NUM=$(echo "$FINAL_BLOCKED" | sed 's/[^0-9.]//g')

# Use bc for floating point arithmetic if available, otherwise use awk
if command -v bc >/dev/null 2>&1; then
    EXPECTED_TOTAL=$(echo "$INITIAL_TOTAL_NUM + $AMOUNT" | bc)
    EXPECTED_BLOCKED=$(echo "$INITIAL_BLOCKED_NUM + $AMOUNT" | bc)
    TOTAL_DIFF=$(echo "$FINAL_TOTAL_NUM - $INITIAL_TOTAL_NUM" | bc)
    BLOCKED_DIFF=$(echo "$FINAL_BLOCKED_NUM - $INITIAL_BLOCKED_NUM" | bc)
else
    # Fallback to awk
    EXPECTED_TOTAL=$(awk "BEGIN {printf \"%.2f\", $INITIAL_TOTAL_NUM + $AMOUNT}")
    EXPECTED_BLOCKED=$(awk "BEGIN {printf \"%.2f\", $INITIAL_BLOCKED_NUM + $AMOUNT}")
    TOTAL_DIFF=$(awk "BEGIN {printf \"%.2f\", $FINAL_TOTAL_NUM - $INITIAL_TOTAL_NUM}")
    BLOCKED_DIFF=$(awk "BEGIN {printf \"%.2f\", $FINAL_BLOCKED_NUM - $INITIAL_BLOCKED_NUM}")
fi

# Check if differences are close to expected amount (allow small floating point differences)
TOLERANCE=0.01
if command -v bc >/dev/null 2>&1; then
    TOTAL_CHECK=$(echo "$TOTAL_DIFF >= ($AMOUNT - $TOLERANCE) && $TOTAL_DIFF <= ($AMOUNT + $TOLERANCE)" | bc)
    BLOCKED_CHECK=$(echo "$BLOCKED_DIFF >= ($AMOUNT - $TOLERANCE) && $BLOCKED_DIFF <= ($AMOUNT + $TOLERANCE)" | bc)
else
    # Simple check with awk (less precise)
    TOTAL_CHECK=$(awk "BEGIN {print ($TOTAL_DIFF >= ($AMOUNT - $TOLERANCE) && $TOTAL_DIFF <= ($AMOUNT + $TOLERANCE))}")
    BLOCKED_CHECK=$(awk "BEGIN {print ($BLOCKED_DIFF >= ($AMOUNT - $TOLERANCE) && $BLOCKED_DIFF <= ($AMOUNT + $TOLERANCE))}")
fi

echo "4. Balance verification:"
echo "   Total Balance Increase: $TOTAL_DIFF AED (expected: $AMOUNT AED)"
echo "   Blocked Balance Increase: $BLOCKED_DIFF AED (expected: $AMOUNT AED)"

if [ "$TOTAL_CHECK" != "1" ]; then
    echo "ERROR: Total balance did not increase by $AMOUNT AED"
    exit 1
fi

if [ "$BLOCKED_CHECK" != "1" ]; then
    echo "ERROR: Blocked balance did not increase by $AMOUNT AED"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ Smoke test PASSED"
echo "═══════════════════════════════════════════════════════════"

