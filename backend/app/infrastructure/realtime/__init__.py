"""Real-time infrastructure package.

Single-instance, in-process implementation of event fan-out.

Architecture note:
    This implementation supports real-time behavior within ONE backend instance.
    For horizontally-scaled multi-instance deployment, replace
    ``InProcessEventPublisher`` with a distributed publisher backed by
    Redis Pub/Sub (or equivalent).  The publisher protocol / abstraction
    allows this swap without touching any domain or service code.
"""
