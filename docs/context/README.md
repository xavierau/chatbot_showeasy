# ShowEasy.ai Platform Context Documentation

This directory contains modular context files for the ShowEasy.ai event platform customer service agent.

## Context Files Overview

### Core Context
1. **[01_platform_overview.md](01_platform_overview.md)** - Platform mission, business model, and value proposition
2. **[02_membership_program.md](02_membership_program.md)** - Membership benefits, pricing, and promotion strategies
3. **[03_event_categories.md](03_event_categories.md)** - Event types, categories, and classification
4. **[04_customer_service.md](04_customer_service.md)** - Service philosophy, tone, voice, and principles
5. **[05_business_scope.md](05_business_scope.md)** - In-scope vs out-of-scope boundaries
6. **[06_response_guidelines.md](06_response_guidelines.md)** - Response templates, formatting, and examples
7. **[07_security_compliance.md](07_security_compliance.md)** - Security policies, compliance, and guardrails

### Supporting Context
8. **[08_user_journeys.md](08_user_journeys.md)** - Common user flows and scenarios
9. **[09_brand_voice.md](09_brand_voice.md)** - Brand voice examples, dos and don'ts

## Usage

These context files are loaded by the `GetPlatformContext` tool, which provides relevant background information to the AI agent based on:
- User intent
- Conversation topic
- Current task

The modular approach allows:
- **Selective loading** - Only relevant context is loaded, reducing token usage
- **Easy maintenance** - Update specific sections without affecting others
- **Caching** - Frequently accessed contexts are cached for performance
- **Scalability** - Add new context types without restructuring

## For Developers

To add new context:
1. Create a new markdown file with descriptive name (e.g., `10_refund_policies.md`)
2. Update this README with a description
3. Update `src/app/utils/context_loader.py` topic mapping if needed
4. Context will be automatically available to the agent

## Version
- **Last Updated**: 2025-10-06
- **Version**: 1.0
