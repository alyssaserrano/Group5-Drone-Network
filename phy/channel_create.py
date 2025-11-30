def create_channel(env, tech_profile):
    channel_cls = getattr(tech_profile, 'channel_class', None)
    channel_params = getattr(tech_profile, 'channel_params', {}) or {}
    if channel_cls is None:
        from .channel import Channel  # Fallback to default
        channel_cls = Channel
    return channel_cls(env, **channel_params)
