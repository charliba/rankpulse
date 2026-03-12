"""Huey tasks for the campaign optimizer — periodic + on-demand."""
from huey.contrib.djhuey import task, periodic_task
from huey import crontab


@task()
def run_optimizer_cycle(channel_id: int) -> dict:
    """On-demand: run a single optimization cycle for a channel."""
    from .models import Channel
    from .optimizer import CampaignOptimizer

    channel = Channel.objects.get(pk=channel_id)
    optimizer = CampaignOptimizer(channel)
    return optimizer.run_optimization_cycle()


@periodic_task(crontab(hour="*/4", minute="0"))
def auto_optimizer_all():
    """Every 4 hours: run optimizer for all enabled channels."""
    from .models import Channel
    from .optimizer import CampaignOptimizer

    channels = Channel.objects.filter(
        optimizer_config__enabled=True,
    ).select_related("optimizer_config")

    for channel in channels:
        try:
            optimizer = CampaignOptimizer(channel)
            optimizer.run_optimization_cycle()
        except Exception as exc:
            import logging
            logging.getLogger("optimizer").error(
                "auto_optimizer failed for channel %s: %s", channel.name, exc
            )
