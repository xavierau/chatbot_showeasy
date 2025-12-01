# Mem0 Azure OpenAI Configuration Bug

**Date:** 2025-11-28
**Status:** Resolved (with workaround)
**Severity:** Medium
**Component:** Mem0 Long-Term Memory Integration

## Issue Description

When integrating Mem0 as a long-term memory service with Azure OpenAI as the LLM and embedder provider, multiple configuration errors occurred preventing Mem0 from initializing and storing memories.

## Symptoms

### Error 1: Missing Azure Module
```
Mem0 service unavailable - continuing without long-term memory
error="No module named 'azure'"
```

### Error 2: Invalid Embedder Configuration
```
Mem0 service unavailable - continuing without long-term memory
error="BaseEmbedderConfig.__init__() got an unexpected keyword argument 'api_base'"
```

### Error 3: Missing Method in AzureOpenAIStructuredLLM
```
Failed to add memory: 'AzureOpenAIStructuredLLM' object has no attribute '_parse_response'
AttributeError: 'AzureOpenAIStructuredLLM' object has no attribute '_parse_response'
```

## Root Cause Analysis

### Error 1: Missing Azure SDK
The `azure-identity` package was not installed in the virtual environment.

### Error 2: Incorrect Embedder Configuration Format
The original `client.py` was using the wrong configuration format for Azure OpenAI embedder:
```python
# WRONG - Old format
embedder_config["api_base"] = self.azure_api_base
embedder_config["api_version"] = self.azure_api_version
```

Mem0 v1.0.x requires `azure_kwargs` dictionary:
```python
# CORRECT - New format
embedder_config["azure_kwargs"] = {
    "api_key": self.embedder_api_key,
    "azure_endpoint": self.azure_api_base,
    "api_version": self.azure_api_version,
    "azure_deployment": self.embedder_model,
}
```

### Error 3: Bug in mem0ai v1.0.1
The `azure_openai_structured` provider in mem0ai v1.0.1 has a bug where the `AzureOpenAIStructuredLLM` class is missing the `_parse_response` method. This is a package bug, not a configuration issue.

**Stack Trace Location:**
- `mem0/llms/azure_openai_structured.py:91` calls `self._parse_response(response, tools)` but the method doesn't exist.

## Solution Implemented

### Fix 1: Install Azure SDK
```bash
uv pip install azure-identity openai
```

### Fix 2: Update Embedder Configuration
Modified `src/app/services/mem0/client.py` `_build_embedder_config()`:
```python
def _build_embedder_config(self) -> Dict[str, Any]:
    embedder_config: Dict[str, Any] = {"model": self.embedder_model}

    if self.embedder_provider in ("azure", "azure_openai"):
        # Mem0 uses azure_kwargs for Azure OpenAI embedder configuration
        azure_kwargs: Dict[str, Any] = {}
        if self.embedder_api_key:
            azure_kwargs["api_key"] = self.embedder_api_key
        if self.azure_api_base:
            azure_kwargs["azure_endpoint"] = self.azure_api_base
        if self.azure_api_version:
            azure_kwargs["api_version"] = self.azure_api_version
        azure_kwargs["azure_deployment"] = self.embedder_model
        embedder_config["azure_kwargs"] = azure_kwargs
    # ... rest of method
```

### Fix 3: Use `azure_openai` Instead of `azure_openai_structured`
Modified `src/app/services/mem0/client.py` `_build_llm_config()`:
```python
if self.llm_provider in ("azure", "azure_openai"):
    # Use azure_openai provider (not azure_openai_structured which has a bug in v1.0.1)
    provider = "azure_openai"  # NOT "azure_openai_structured"
    azure_kwargs: Dict[str, Any] = {
        "azure_deployment": self.llm_model,
    }
    # ... rest of config
```

## Alternative Solutions

If Azure OpenAI continues to have issues, use one of these alternatives:

### Option A: Use OpenAI Directly
```bash
# .env
MEM0_LLM_PROVIDER=openai
MEM0_LLM_MODEL=gpt-4o-mini
MEM0_LLM_API_KEY=your_openai_api_key

MEM0_EMBEDDER_PROVIDER=openai
MEM0_EMBEDDER_MODEL=text-embedding-3-small
MEM0_EMBEDDER_API_KEY=your_openai_api_key
```

### Option B: Use Gemini
```bash
# .env
MEM0_LLM_PROVIDER=gemini
MEM0_LLM_MODEL=gemini-2.0-flash

MEM0_EMBEDDER_PROVIDER=gemini
MEM0_EMBEDDER_MODEL=models/text-embedding-004
```

### Option C: Disable Mem0
```bash
# .env
MEM0_ENABLED=false
```

## Files Modified

| File | Changes |
|------|---------|
| `src/app/services/mem0/client.py:162-190` | Updated `_build_llm_config()` to use `azure_openai` provider and `azure_kwargs` |
| `src/app/services/mem0/client.py:192-206` | Updated `_build_embedder_config()` to use `azure_kwargs` |

## Prevention Strategies

1. **Pin mem0ai version** in `pyproject.toml` once a working version is confirmed
2. **Add integration test** that verifies Mem0 initialization with configured provider
3. **Document provider-specific configuration** in `.env.example` with comments
4. **Monitor mem0ai releases** for bug fixes to `azure_openai_structured` provider

## Testing

After applying fixes, verify with:
```bash
# Check Mem0 initializes without errors
PYTHONPATH=src python -c "
from app.services.mem0 import Mem0Service
service = Mem0Service()
print('Mem0 initialized successfully')
"
```

## Related Documentation

- [Mem0 Azure OpenAI Embedder Docs](https://docs.mem0.ai/components/embedders/models/azure_openai)
- [Mem0 Azure OpenAI LLM Docs](https://docs.mem0.ai/components/llms/models/azure_openai)
- Architecture Doc: `docs/architecture/2025-11-28-mem0-long-term-memory-integration.md`

## Lessons Learned

1. **API changes between versions**: Mem0 v1.0.x changed configuration format from flat keys to nested `azure_kwargs`
2. **Provider naming matters**: `azure_openai` vs `azure_openai_structured` are different providers with different implementations
3. **Check package source**: When encountering `AttributeError`, check the package source code to understand expected behavior
4. **Graceful degradation works**: The system correctly fell back to operating without long-term memory when Mem0 failed
