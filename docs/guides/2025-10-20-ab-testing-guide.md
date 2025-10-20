# AB Testing Guide for ConversationOrchestrator

**Created:** 2025-10-20
**Status:** Active
**Purpose:** Guide for implementing and running AB tests on conversation modules

## Overview

The ConversationOrchestrator supports AB testing for three nested modules:
1. **Pre-Guardrails**: Test different input validation models/strategies
2. **Post-Guardrails**: Test different output validation approaches
3. **Agent**: Test different ReAct agent configurations

## Architecture

### Components

1. **ABTestConfig** (`src/app/models/ABTestConfig.py`)
   - Configuration dataclass for AB testing
   - Supports three variants: `CONTROL`, `VARIANT_A`, `VARIANT_B`
   - Independent configuration for each module

2. **ConversationOrchestrator** (`src/app/llm/modules/ConversationOrchestrator.py`)
   - Accepts `ab_config` parameter in `__init__`
   - Initializes modules based on variant configuration
   - Logs variant selection for tracking

3. **get_ab_test_config()** (`src/app/api/main.py`)
   - Hash-based user bucketing for consistent variant assignment
   - Environment variable configuration
   - Automatic distribution across variants

## Usage

### 1. Environment Variables

Configure AB testing via environment variables:

```bash
# Enable AB testing
AB_TEST_ENABLED=true

# Select module to test: pre_guardrails, post_guardrails, or agent
AB_TEST_MODULE=pre_guardrails

# Set distribution percentages (0-100)
AB_TEST_VARIANT_A_RATIO=33  # 33% get variant A
AB_TEST_VARIANT_B_RATIO=33  # 33% get variant B
# Remaining 34% get control (100 - 33 - 33 = 34)
```

### 2. Common Test Scenarios

#### Test Optimized vs Baseline Pre-Guardrails

**Scenario:** Compare GEPA-optimized pre-guardrails against baseline

```bash
export AB_TEST_ENABLED=true
export AB_TEST_MODULE=pre_guardrails
export AB_TEST_VARIANT_A_RATIO=50  # 50% baseline
export AB_TEST_VARIANT_B_RATIO=0   # 0% unused
# 50% control (optimized model)
```

**Variants:**
- **CONTROL**: Optimized model (loaded via `load_optimized_model()`)
- **VARIANT_A**: Baseline model (no optimization)
- **VARIANT_B**: Reserved for future variants

#### Test Agent Iteration Limits

**Scenario:** Test faster response times with reduced max_iters

```bash
export AB_TEST_ENABLED=true
export AB_TEST_MODULE=agent
export AB_TEST_VARIANT_A_RATIO=50  # 50% with max_iters=5
export AB_TEST_VARIANT_B_RATIO=0
# 50% control (max_iters=10)
```

**Variants:**
- **CONTROL**: `max_iters=10` (default)
- **VARIANT_A**: `max_iters=5` (faster, potentially less thorough)
- **VARIANT_B**: Reserved for future variants

#### Three-Way Split Testing

**Scenario:** Test two different approaches against control

```bash
export AB_TEST_ENABLED=true
export AB_TEST_MODULE=post_guardrails
export AB_TEST_VARIANT_A_RATIO=33
export AB_TEST_VARIANT_B_RATIO=33
# 34% control
```

### 3. Programmatic Usage

For custom AB test logic, use the config directly:

```python
from app.models import ABTestConfig, ModuleABConfig, ABVariant
from app.llm.modules import ConversationOrchestrator

# Create custom AB config
ab_config = ABTestConfig(
    pre_guardrails=ModuleABConfig(
        enabled=True,
        variant=ABVariant.VARIANT_A,
        description="Testing baseline pre-guardrails"
    )
)

# Initialize orchestrator with AB config
orchestrator = ConversationOrchestrator(ab_config=ab_config)

# Use as normal
result = orchestrator(
    user_message="What events are happening this weekend?",
    previous_conversation=[],
    page_context=""
)
```

### 4. Monitoring in Langfuse

AB test metadata is automatically logged to Langfuse:

```json
{
  "ab_test": {
    "pre_guardrails": {
      "enabled": true,
      "variant": "variant_a",
      "description": "Baseline pre-guardrails without optimization"
    },
    "post_guardrails": {
      "enabled": false,
      "variant": "control",
      "description": null
    },
    "agent": {
      "enabled": false,
      "variant": "control",
      "description": null
    }
  }
}
```

**Langfuse Query Examples:**

```sql
-- Compare accuracy by variant
SELECT
  metadata->'ab_test'->'pre_guardrails'->>'variant' as variant,
  AVG(CASE WHEN output_valid THEN 1 ELSE 0 END) as accuracy
FROM traces
WHERE metadata->'ab_test' IS NOT NULL
GROUP BY variant;

-- Compare latency by variant
SELECT
  metadata->'ab_test'->'agent'->>'variant' as variant,
  AVG(duration_ms) as avg_latency_ms
FROM traces
WHERE metadata->'ab_test'->'agent'->>'enabled' = 'true'
GROUP BY variant;
```

## Implementation Details

### Hash-Based Bucketing

Users are consistently assigned to variants using MD5 hash:

```python
hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100

if hash_val < variant_a_ratio:
    variant = ABVariant.VARIANT_A
elif hash_val < variant_a_ratio + variant_b_ratio:
    variant = ABVariant.VARIANT_B
else:
    variant = ABVariant.CONTROL
```

**Properties:**
- **Consistent**: Same user always gets same variant
- **Reproducible**: Deterministic based on user_id
- **Even distribution**: Approximately uniform across variants
- **Independent**: Different modules can have different configs

### Module Initialization

Each module has a dedicated initialization method:

1. **`_initialize_pre_guardrails()`**
   - `CONTROL`: Standard with `load_optimized_model()`
   - `VARIANT_A`: Recreates validator without optimization
   - `VARIANT_B`: Reserved

2. **`_initialize_post_guardrails()`**
   - `CONTROL`: Standard PostGuardrails
   - `VARIANT_A`: Reserved
   - `VARIANT_B`: Reserved

3. **`_initialize_agent()`**
   - `CONTROL`: `max_iters=10`
   - `VARIANT_A`: `max_iters=5`
   - `VARIANT_B`: Reserved

## Best Practices

### 1. Hypothesis-Driven Testing

Always define clear hypotheses before running tests:

**Good:**
> "Hypothesis: GEPA-optimized pre-guardrails will reduce false positives by 10% without increasing latency."

**Bad:**
> "Let's test some different settings."

### 2. Sample Size Calculation

Use proper statistical power analysis:

```python
# Example: Detect 5% improvement with 80% power, 95% confidence
from scipy.stats import norm
import math

def required_sample_size(baseline_rate=0.05, target_rate=0.045, alpha=0.05, power=0.8):
    z_alpha = norm.ppf(1 - alpha/2)
    z_beta = norm.ppf(power)

    p1, p2 = baseline_rate, target_rate
    p_avg = (p1 + p2) / 2

    n = ((z_alpha + z_beta)**2 * 2 * p_avg * (1 - p_avg)) / ((p1 - p2)**2)
    return math.ceil(n)

# Detect 5% -> 4.5% false positive rate improvement
print(f"Required sample size per variant: {required_sample_size()}")
# Output: Required sample size per variant: 3382
```

### 3. Monitoring Metrics

Track these key metrics for each variant:

**Pre-Guardrails:**
- False positive rate
- False negative rate
- Average latency
- Violation type distribution

**Post-Guardrails:**
- Violation detection rate
- Sanitization frequency
- Average latency

**Agent:**
- Average number of tool calls
- Success rate
- Average latency
- Tool usage distribution

### 4. Gradual Rollout

Start with small percentages and increase gradually:

```bash
# Week 1: 10% variant
AB_TEST_VARIANT_A_RATIO=10

# Week 2: 25% variant (if metrics look good)
AB_TEST_VARIANT_A_RATIO=25

# Week 3: 50% variant
AB_TEST_VARIANT_A_RATIO=50

# Week 4: Full rollout (100% variant becomes new control)
AB_TEST_ENABLED=false  # Disable test, variant is now default
```

### 5. Statistical Significance

Don't end tests too early. Use proper statistical tests:

```python
from scipy.stats import ttest_ind

# Example: Compare false positive rates
control_fp_rate = [0.05, 0.04, 0.06, ...]  # Per-user rates
variant_fp_rate = [0.03, 0.04, 0.02, ...]

t_stat, p_value = ttest_ind(control_fp_rate, variant_fp_rate)

if p_value < 0.05:
    print(f"✓ Statistically significant improvement (p={p_value:.4f})")
else:
    print(f"✗ No significant difference (p={p_value:.4f})")
```

## Troubleshooting

### Issue: Users getting different variants on each request

**Cause:** Inconsistent `user_id` values (e.g., changing session IDs)

**Solution:** Ensure `user_id` is stable across requests

### Issue: Uneven distribution (e.g., 60/40 instead of 50/50)

**Cause:** Hash function properties with small sample sizes

**Solution:** This is expected with small N. With N>100, distribution should be ~±3%

### Issue: AB test config not being applied

**Cause:** Environment variables not set or `AB_TEST_ENABLED=false`

**Solution:** Verify environment variables:
```bash
echo $AB_TEST_ENABLED
echo $AB_TEST_MODULE
echo $AB_TEST_VARIANT_A_RATIO
```

### Issue: Langfuse not showing AB test metadata

**Cause:** Config is default (all control)

**Solution:** Ensure `ab_config.is_any_variant_active()` returns `True`

## Examples

### Example 1: Test Optimized Pre-Guardrails

**Goal:** Validate GEPA optimization improves accuracy without degrading latency

**Setup:**
```bash
export AB_TEST_ENABLED=true
export AB_TEST_MODULE=pre_guardrails
export AB_TEST_VARIANT_A_RATIO=50  # 50% baseline
export AB_TEST_VARIANT_B_RATIO=0
```

**Metrics to Track:**
- Accuracy (is_valid correctness)
- False positive rate
- Latency (p50, p95, p99)

**Success Criteria:**
- Accuracy improvement ≥10%
- False positive rate <5%
- Latency increase <10%

### Example 2: Test Agent Iteration Optimization

**Goal:** Reduce latency by limiting agent iterations without sacrificing quality

**Setup:**
```bash
export AB_TEST_ENABLED=true
export AB_TEST_MODULE=agent
export AB_TEST_VARIANT_A_RATIO=33  # max_iters=5
export AB_TEST_VARIANT_B_RATIO=0
```

**Metrics to Track:**
- Response quality (user ratings)
- Average tool calls per request
- Latency (p50, p95)
- Success rate

**Success Criteria:**
- Latency reduction ≥20%
- Quality degradation <5%
- Success rate unchanged

## Related Documentation

- [Architecture: Guardrails System](../architecture/2025-10-20-guardrails-architecture.md)
- [Guide: GEPA Optimization](../guides/2025-10-20-gepa-optimization.md)
- [Debugging: AB Test Issues](../../debugging_journals/2025-10-20-ab-test-debugging.md)

## Changelog

- **2025-10-20**: Initial AB testing implementation
  - Added `ABTestConfig` dataclass
  - Implemented hash-based bucketing
  - Integrated with ConversationOrchestrator
  - Added Langfuse metadata logging
