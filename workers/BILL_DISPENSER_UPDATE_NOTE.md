# BillDispenserWorker API Update

The `BillDispenserWorker` in `workers/threads.py` needs a small update to use the new modular dispense_bill() API.

## Change Required

**File:** `workers/threads.py`  
**Line:** ~66

**Current code:**

```python
ok_disp, msg = self.handler.dispense_bill(denom, qty, self.dispense_time_ms)
```

**Updated code:**

```python
# New modular API: dispense_duration_s instead of dispense_time_ms
ok_disp, msg = self.handler.dispense_bill(
    denom=denom,
    qty=qty,
    dispense_duration_s=self.dispense_time_ms / 1000.0  # Convert ms to seconds
)
```

## Why This Change?

The new modular `dispense_bill()` method uses:

- Named parameters for clarity
- `dispense_duration_s` (seconds) instead of `dispense_time_ms` (milliseconds)

This makes the API more consistent with the other timing parameters in the system.
