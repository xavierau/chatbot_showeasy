# ShowEasy.ai Platform Context Documentation

This directory contains modular context files for the ShowEasy.ai event platform customer service agent.

## About Show Easy Group

**ShowEasy.ai** is the AI-powered ticketing and membership platform of **Show Easy Group**, a Hong Kong-based company dedicated to supporting the performing arts ecosystem.

### Show Easy Group's Three Core Businesses

1. **DDC Creative Content**: Supporting original Hong Kong performance IP development from concept to stage
2. **Performance-Themed Venues**: Restaurants that combine dining with original performance experiences
3. **Show Easy Membership and Ticketing AI Platform** (ShowEasy.ai): Technology-driven platform connecting audiences with creators

### Mission
Help all dreamers in Hong Kong—whether on stage or behind the scenes—find their own stage, while creating iconic performances that represent Hong Kong on the international cultural stage.

## Context Files Overview

### Core Context (Currently Available)
1. **[01_platform_overview.md](01_platform_overview.md)** - Show Easy Group ecosystem, platform mission, business model, and value proposition
2. **[02_membership_program.md](02_membership_program.md)** - Membership benefits, pricing, promotion strategies, and how it supports Hong Kong creators
3. **[03_event_categories.md](03_event_categories.md)** - Event types, categories, Hong Kong original content priority, and performance-themed venues
4. **[04_customer_service.md](04_customer_service.md)** - Service philosophy aligned with Show Easy Group mission, tone, voice, and principles
5. **[05_contact_information.md](05_contact_information.md)** - Contact details, response times, escalation guidelines, and when to provide contact info

### Planned Context (To Be Created)
6. **[06_business_scope.md](06_business_scope.md)** - In-scope vs out-of-scope boundaries
7. **[07_response_guidelines.md](07_response_guidelines.md)** - Response templates, formatting, and examples
8. **[08_security_compliance.md](08_security_compliance.md)** - Security policies, compliance, and guardrails
9. **[09_user_journeys.md](09_user_journeys.md)** - Common user flows and scenarios
10. **[10_brand_voice.md](10_brand_voice.md)** - Brand voice examples, dos and don'ts

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
- **Last Updated**: 2025-10-19
- **Version**: 1.1
- **Changes**: Added 05_contact_information.md with complete contact details and escalation guidelines
