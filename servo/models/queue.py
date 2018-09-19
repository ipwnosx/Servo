# -*- coding: utf-8 -*-

from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from servo import defaults
from servo.models.common import Location


class Queue(models.Model):
    title = models.CharField(
        max_length=255,
        unique=True,
        default=_('New Queue'),
        verbose_name=_('Title')
    )

    keywords = models.TextField(
        default='',
        blank=True,
        help_text=_('Orders with devices matching these keywords will be automatically assigned to this queue')
    )

    locations = models.ManyToManyField(
        Location,
        verbose_name=_('locations'),
        help_text=_("Pick the locations you want this queue to appear in.")
    )

    description = models.TextField(
        blank=True,
        verbose_name=_('description')
    )

    PRIO_LOW    = 0
    PRIO_NORMAL = 1
    PRIO_HIGH   = 2

    PRIORITIES = (
        (PRIO_HIGH, _("High")),
        (PRIO_NORMAL, _("Normal")),
        (PRIO_LOW, _("Low"))
    )

    priority = models.IntegerField(
        default=PRIO_NORMAL,
        choices=PRIORITIES,
        verbose_name=_("priority")
    )

    status_created = models.ForeignKey(
        'QueueStatus',
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_(u'Order Created'),
        help_text=_("Order has ben placed into a queue"),
        on_delete=models.SET_NULL
    )

    status_assigned = models.ForeignKey(
        'QueueStatus',
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_(u'Order Assigned'),
        help_text=_("Order has ben assigned to a user"),
        on_delete=models.SET_NULL
    )

    status_products_ordered = models.ForeignKey(
        'QueueStatus',
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_("Products Ordered"),
        help_text=_("Purchase Order for this Service Order has been submitted"),
        on_delete=models.SET_NULL
    )
    status_products_received = models.ForeignKey(
        'QueueStatus',
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_("Products Received"),
        help_text=_("Products have been received"),
        on_delete=models.SET_NULL
    )
    status_repair_completed = models.ForeignKey(
        'QueueStatus',
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_("Repair Completed"),
        help_text=_("GSX repair completed"),
        on_delete=models.SET_NULL
    )

    status_dispatched = models.ForeignKey(
        'QueueStatus',
        null=True,
        blank=True,
        related_name='+',
        on_delete=models.SET_NULL,
        verbose_name=_("Order Dispatched"),
    )

    status_closed = models.ForeignKey(
        'QueueStatus',
        null=True,
        blank=True,
        related_name='+',
        on_delete=models.SET_NULL,
        verbose_name=_("Order Closed"),
    )

    gsx_soldto = models.CharField(
        blank=True,
        default='',
        max_length=10,
        verbose_name=_("Sold-To"),
        help_text=_("GSX queries of an order in this queue will be made using this Sold-To"),
    )

    order_template = models.FileField(
        null=True,
        blank=True,
        upload_to="templates",
        verbose_name=_("order template"),
        help_text=_("HTML template for Service Order/Work Confirmation")
    )
    quote_template = models.FileField(
        null=True,
        blank=True,
        upload_to="templates",
        verbose_name=_("quote template"),
        help_text=_("HTML template for cost estimate")
    )
    receipt_template = models.FileField(
        null=True,
        blank=True,
        upload_to="templates",
        verbose_name=_("receipt template"),
        help_text=_("HTML template for Sales Order Receipt")
    )
    dispatch_template = models.FileField(
        null=True,
        blank=True,
        upload_to="templates",
        verbose_name=_("dispatch template"),
        help_text=_("HTML template for dispatched order")
    )

    def get_admin_url(self):
        return reverse('admin-edit_queue', args=[self.pk])

    def get_absolute_url(self):
        p = '?queue=%d' % self.pk
        return reverse('orders-index') + p

    def get_order_count(self, max_state=2):
        count = self.order_set.filter(state__lt=max_state).count()
        return count if count > 0 else ''

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ['title']
        app_label = "servo"
        verbose_name = _("Queue")
        verbose_name_plural = _("Queues")


class Status(models.Model):
    FACTOR_CHOICES = (
        (60,        _('Minutes')),
        (3600,      _('Hours')),
        (86400,     _('Days')),
        (604800,    _('Weeks')),
        (2419200,   _('Months')),
    )

    title = models.CharField(
        max_length=255,
        default=_(u'New Status'),
        verbose_name=_(u'name')
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name=_(u'description')
    )
    limit_green = models.IntegerField(
        default=1,
        verbose_name=_(u'green limit')
    )
    limit_yellow = models.IntegerField(
        default=15,
        verbose_name=_(u'yellow limit')
    )
    limit_factor = models.IntegerField(
        choices=FACTOR_CHOICES,
        default=FACTOR_CHOICES[0],
        verbose_name=_(u'time unit')
    )
    queue = models.ManyToManyField(
        Queue,
        editable=False,
        through='QueueStatus'
    )

    def is_enabled(self, queue):
        return self in queue.queuestatus_set.all()

    def get_admin_url(self):
        return reverse('admin-edit_status', args=[self.pk])

    def __unicode__(self):
        return self.title

    class Meta:
        app_label = 'servo'
        ordering = ('title',)
        verbose_name = _('Status')
        verbose_name_plural = _('Statuses')


class QueueStatus(models.Model):
    """
    A status bound to a queue.
    This allows us to set time limits for each status per indiviudal queue
    """
    queue  = models.ForeignKey(Queue, on_delete=models.CASCADE)
    status = models.ForeignKey(Status, on_delete=models.CASCADE)

    limit_green = models.IntegerField(default=1, verbose_name=_(u'Green limit'))
    limit_yellow = models.IntegerField(default=15, verbose_name=_(u'Yellow limit'))
    limit_factor = models.IntegerField(
        choices=Status.FACTOR_CHOICES,
        verbose_name=_(u'Time unit'),
        default=Status.FACTOR_CHOICES[0][0]
    )

    idx = models.IntegerField(default=1, verbose_name=_(u'Ordering'))

    def get_green_limit(self):
        """
        Gets the green time limit for this QS
        """
        sec = self.limit_green * self.limit_factor
        return timezone.now() + timedelta(seconds=sec)

    def get_yellow_limit(self):
        sec = self.limit_yellow * self.limit_factor
        return timezone.now() + timedelta(seconds=sec)

    def __unicode__(self):
        return self.status.title

    class Meta:
        app_label = 'servo'
        ordering = ('idx',)
        # A status should only be defined once per queue
        unique_together = ('queue', 'status',)
