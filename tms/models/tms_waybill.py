# -*- coding: utf-8 -*-
# Copyright 2012, Israel Cruz Argil, Argil Consulting
# Copyright 2016, Jarsa Sistemas, S.A. de C.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from __future__ import division

import logging

from openerp import _, api, exceptions, fields, models

_logger = logging.getLogger(__name__)
try:
    from num2words import num2words
except ImportError:
    _logger.debug('Cannot `import num2words`.')


class TmsWaybill(models.Model):
    _name = 'tms.waybill'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Waybills'
    _order = 'name desc'

    operating_unit_id = fields.Many2one(
        'operating.unit', string='Operating Unit', required=True)
    customer_factor_ids = fields.One2many(
        'tms.factor', 'waybill_id',
        string='Waybill Customer Charge Factors',
        domain=[('category', '=', 'customer'), ])
    supplier_factor_ids = fields.One2many(
        'tms.factor', 'waybill_id',
        string='Waybill Supplier Payment Factors',
        domain=[('category', '=', 'supplier'), ])
    driver_factor_ids = fields.One2many(
        'tms.factor', 'waybill_id',
        string='Travel Driver Payment Factors',
        domain=[('category', '=', 'driver'), ])
    transportable_line_ids = fields.One2many(
        'tms.waybill.transportable.line', 'waybill_id', string="Transportable"
    )
    tax_line_ids = fields.One2many(
        'tms.waybill.taxes', 'waybill_id',
        string='Tax Lines', store=True)
    name = fields.Char()
    travel_ids = fields.Many2many(
        'tms.travel',
        string='Travels')
    origin = fields.Char(
        'Source Document',
        help="Reference of the document that generated this Waybill request.")
    client_order_ref = fields.Char(
        'Customer Reference')
    state = fields.Selection([
        ('draft', 'Pending'),
        ('approved', 'Approved'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled')], readonly=True,
        help="Gives the state of the Waybill.",
        default='draft')
    date_order = fields.Datetime(
        'Date', required=True,
        default=fields.Datetime.now)
    user_id = fields.Many2one(
        'res.users', 'Salesman',
        default=(lambda self: self.env.user))
    partner_id = fields.Many2one(
        'res.partner',
        'Customer', required=True, change_default=True)
    currency_id = fields.Many2one(
        'res.currency', 'Currency', required=True,
        default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    partner_invoice_id = fields.Many2one(
        'res.partner', 'Invoice Address', required=True,
        help="Invoice address for current Waybill.",
        default=(lambda self: self.env[
            'res.partner'].address_get(
            self['partner_id'])))
    partner_order_id = fields.Many2one(
        'res.partner', 'Ordering Contact', required=True,
        help="The name and address of the contact who requested the "
        "order or quotation.",
        default=(lambda self: self.env['res.partner'].address_get(
            self['partner_id'])['contact']))
    departure_address_id = fields.Many2one(
        'res.partner', 'Departure Address', required=True,
        help="Departure address for current Waybill.", change_default=True)
    arrival_address_id = fields.Many2one(
        'res.partner', 'Arrival Address', required=True,
        help="Arrival address for current Waybill.", change_default=True)
    upload_point = fields.Char(change_default=True)
    download_point = fields.Char(change_default=True)
    invoice_id = fields.Many2one(
        'account.invoice', 'Invoice', readonly=True, copy=False)
    invoice_paid = fields.Boolean(
        compute="_compute_invoice_paid")
    supplier_invoice_id = fields.Many2one(
        'account.invoice', string='Supplier Invoice', readonly=True)
    supplier_invoice_paid = fields.Boolean(
        compute='_compute_supplier_invoice_paid',
        readonly=True)
    waybill_line_ids = fields.One2many(
        'tms.waybill.line', 'waybill_id',
        string='Waybill Lines')
    transportable_ids = fields.One2many(
        'tms.waybill.transportable.line', 'waybill_id',
        string='Shipped Products')
    product_qty = fields.Float(
        compute='_compute_transportable_product',
        string='Sum Qty')
    product_volume = fields.Float(
        compute='_compute_transportable_product',
        string='Sum Volume')
    product_weight = fields.Float(
        compute='_compute_transportable_product',
        string='Sum Weight')
    amount_freight = fields.Float(
        compute='_compute_amount_freight',
        string='Freight')
    amount_move = fields.Float(
        compute='_compute_amount_move',
        string='Moves')
    amount_highway_tolls = fields.Float(
        compute='_compute_amount_highway_tolls',
        string='Highway Tolls')
    amount_insurance = fields.Float(
        compute='_compute_amount_insurance',
        string='Insurance')
    amount_other = fields.Float(
        compute='_compute_amount_other',
        string='Other')
    amount_untaxed = fields.Float(
        compute='_compute_amount_untaxed',
        string='SubTotal')
    amount_tax = fields.Float(
        compute='_compute_amount_tax',
        string='Taxes')
    amount_total = fields.Float(
        compute='_compute_amount_total',
        string='Total')
    distance_real = fields.Float(
        help="Route obtained by electronic reading")
    distance_route = fields.Float()
    notes = fields.Html()
    date_start = fields.Datetime(
        'Load Date Sched', help="Date Start time for Load",
        default=fields.Datetime.now)
    date_up_start_sched = fields.Datetime(
        'UpLd Start Sched',
        default=fields.Datetime.now)
    date_up_end_sched = fields.Datetime(
        'UpLd End Sched',
        default=fields.Datetime.now)
    date_up_docs_sched = fields.Datetime(
        'UpLd Docs Sched',
        default=fields.Datetime.now)
    date_appoint_down_sched = fields.Datetime(
        'Download Date Sched',
        default=fields.Datetime.now)
    date_down_start_sched = fields.Datetime(
        'Download Start Sched',
        default=fields.Datetime.now)
    date_down_end_sched = fields.Datetime(
        'Download End Sched',
        default=fields.Datetime.now)
    date_down_docs_sched = fields.Datetime(
        'Download Docs Sched',
        default=fields.Datetime.now)
    date_end = fields.Datetime(
        'Travel End Sched', help="Date End time for Load",
        default=fields.Datetime.now)
    date_start_real = fields.Datetime('Load Date Real')
    date_up_start_real = fields.Datetime('UpLoad Start Real')
    date_up_end_real = fields.Datetime('UpLoad End Real')
    date_up_docs_real = fields.Datetime('Load Docs Real')
    date_appoint_down_real = fields.Datetime('Download Date Real')
    date_down_start_real = fields.Datetime('Download Start Real')
    date_down_end_real = fields.Datetime('Download End Real')
    date_down_docs_real = fields.Datetime('Download Docs Real')
    date_end_real = fields.Datetime('Travel End Real')
    amount_declared = fields.Float(
        help=" Load value amount declared for insurance purposes...")
    replaced_waybill_id = fields.Many2one(
        'tms.waybill', 'Replaced Waybill', readonly=True)
    move_id = fields.Many2one(
        'account.move', string='Journal Entry', readonly=True)
    client_order_ref = fields.Char(
        'Customer Reference', size=64, readonly=False,
        states={'confirmed': [('readonly', True)]})
    billing_policy = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic'), ],
        readonly=False,
        states={'confirmed': [('readonly', True)]},
        help="Gives the state of the Waybill. \n "
        "-The exception state is automatically set "
        "when a cancel operation occurs in the invoice "
        "validation (Invoice Exception) or in the picking "
        "list process (Shipping Exception). \n"
        "The 'Waiting Schedule' state is set when the invoice "
        "is confirmed but waiting for the scheduler to run on "
        "the date 'Ordered Date'.", index=True, default='manual')
    waybill_extradata = fields.One2many(
        'tms.extradata', 'waybill_id',
        string='Extra Data Fields',
        readonly=False, states={'confirmed': [('readonly', True)]})
    custom_ids = fields.One2many(
        'tms.customs',
        'waybill_id',
        string="Customs")
    rate = fields.Float(compute="_compute_rate")

    @api.depends('date_order')
    def _compute_rate(self):
        """Get the exchange rate in the invoice date to set in the XML."""
        currency_mxn = self.env.ref('base.MXN')
        for record in self.filtered(lambda r: r.date_order):
            currency = record.currency_id.with_context(
                date=record.date_order)
            record.rate = currency.compute(1, currency_mxn)

    @api.model
    def create(self, values):
        waybill = super(TmsWaybill, self).create(values)
        sequence = waybill.operating_unit_id.waybill_sequence_id
        waybill.name = sequence.next_by_id()
        product = self.env['product.product'].search([
            ('tms_product_category', '=', 'freight')])
        if product:
            self.waybill_line_ids.create({
                'name': product.name,
                'waybill_id': waybill.id,
                'product_id': product.id,
                'tax_ids': [(
                    6, 0, [x.id for x in (
                        product.taxes_id)]
                )],
                'account_id': product.property_account_income_id.id,
            })
        waybill._compute_transportable_product()
        waybill.onchange_waybill_line_ids()

        return waybill

    @api.multi
    def copy(self, default=None):
        default = dict(default or {})
        default['travel_ids'] = False
        return super(TmsWaybill, self).copy(default)

    @api.multi
    def write(self, values):
        for rec in self:
            if 'partner_id' in values:
                for travel in rec.travel_ids:
                    travel.partner_ids = False
                    travel._compute_partner_ids()
            res = super(TmsWaybill, self).write(values)
            return res

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.partner_order_id = self.partner_id.address_get(
                ['invoice', 'contact']).get('contact', False)
            self.partner_invoice_id = self.partner_id.address_get(
                ['invoice', 'contact']).get('invoice', False)

    @api.multi
    def action_approve(self):
        for waybill in self:
            waybill.state = 'approved'
            self.message_post(body=_(
                "<h5><strong>Aprroved</strong></h5>"
                "<p><strong>Approved by: </strong> %s <br>"
                "<strong>Approved at: </strong> %s</p") % (
                self.user_id.name, fields.Date.today()))
        return True

    @api.multi
    @api.depends('invoice_id')
    def _compute_invoice_paid(self):
        for rec in self:
            paid = (rec.invoice_id and rec.invoice_id.state == 'paid')
            rec.invoice_paid = paid

    @api.depends('transportable_line_ids', 'customer_factor_ids')
    def _compute_transportable_product(self):
        for waybill in self:
            volume = weight = qty = distance_real = distance_route = 0
            control = ""
            for record in waybill.transportable_line_ids:
                total = 0.0
                for factor in waybill.customer_factor_ids:
                    qty = record.quantity
                    if (record.transportable_uom_id.category_id.name ==
                            _('Volume')):
                        volume += record.quantity
                        control = "volume"
                    elif (record.transportable_uom_id.category_id.name ==
                            _('Weight')):
                        weight += record.quantity
                        control = "weight"
                    elif (record.transportable_uom_id.category_id.name ==
                            _('Length / Distance')):
                        if factor.factor_type == 'distance':
                            distance_route += record.quantity
                            control = "distance"
                        else:
                            distance_real += record.quantity
                            control = "distance_real"
                    waybill.product_qty = qty
                    waybill.product_volume = volume
                    waybill.product_weight = weight
                    waybill.distance_route = distance_route
                    waybill.distance_real = distance_real
                    if factor.factor_type != control and (
                        factor.factor_type not in [
                            'travel', 'percent', 'qty', 'percent_driver']):
                        raise exceptions.ValidationError(
                            _('Check the type of customer factor for the '
                              'product to be transported.'))
                    total_get_amount = waybill.customer_factor_ids.get_amount(
                        waybill.product_weight, waybill.distance_route,
                        waybill.distance_real, waybill.product_qty,
                        waybill.product_volume, waybill.amount_total)
                    total = (total + total_get_amount)
                    for product in waybill.waybill_line_ids:
                        if (product.product_id.tms_product_category ==
                                'freight'):
                            product.write({'unit_price': total})

    @api.multi
    def _compute_amount_all(self, category):
        for waybill in self:
            field = 0.0
            for line in waybill.waybill_line_ids:
                if (line.product_id.tms_product_category ==
                        category):
                    field += line.price_subtotal
            return field

    @api.depends('waybill_line_ids')
    def _compute_amount_freight(self):
        for rec in self:
            rec.amount_freight = rec._compute_amount_all('freight')

    @api.depends('waybill_line_ids')
    def _compute_amount_move(self):
        for rec in self:
            rec.amount_move = rec._compute_amount_all('move')

    @api.depends('waybill_line_ids')
    def _compute_amount_highway_tolls(self):
        for rec in self:
            rec.amount_highway_tolls = rec._compute_amount_all('tolls')

    @api.depends('waybill_line_ids')
    def _compute_amount_insurance(self):
        for rec in self:
            rec.amount_insurance = rec._compute_amount_all('insurance')

    @api.depends('waybill_line_ids')
    def _compute_amount_other(self):
        for rec in self:
            rec.amount_other = rec._compute_amount_all('other')

    @api.depends('waybill_line_ids')
    def _compute_amount_untaxed(self):
        for waybill in self:
            for line in waybill.waybill_line_ids:
                waybill.amount_untaxed += line.price_subtotal

    @api.depends('waybill_line_ids')
    def _compute_amount_tax(self):
        for waybill in self:
            for line in waybill.waybill_line_ids:
                waybill.amount_tax += line.tax_amount

    @api.depends('amount_untaxed', 'amount_tax')
    def _compute_amount_total(self):
        for waybill in self:
            waybill.amount_total = waybill.amount_untaxed + waybill.amount_tax

    @api.multi
    def action_confirm(self):
        for waybill in self:
            if not waybill.travel_ids:
                raise exceptions.ValidationError(
                    _('Could not confirm Waybill !\n'
                      'Waybill must be assigned to a Travel before '
                      'confirming.'))
            waybill.state = 'confirmed'

    @api.onchange('waybill_line_ids')
    def onchange_waybill_line_ids(self):
        for waybill in self:
            tax_grouped = {}
            for line in waybill.waybill_line_ids:

                unit_price = (
                    line.unit_price * (1 - (line.discount or 0.0) / 100.0))
                taxes = line.tax_ids.compute_all(
                    unit_price, waybill.currency_id, line.product_qty,
                    line.product_id, waybill.partner_id)
                for tax in taxes['taxes']:
                    val = {
                        'tax_id': tax['id'], 'base': taxes['base'],
                        'tax_amount': tax['amount']}
                    key = waybill.env['account.tax'].browse(tax['id']).id
                    if key not in tax_grouped:
                        tax_grouped[key] = val
                    else:
                        tax_grouped[key]['tax_amount'] += val['tax_amount']
                        tax_grouped[key]['base'] += val['base']
            tax_lines = waybill.tax_line_ids.browse([])
            for tax in tax_grouped.values():
                tax_lines += tax_lines.new(tax)
            waybill.tax_line_ids = tax_lines

    @api.multi
    def action_cancel_draft(self):
        for waybill in self:
            for travel in waybill.travel_ids:
                if travel.state == 'cancel':
                    raise exceptions.ValidationError(
                        _('Could not set to draft this Waybill !\n'
                          'Travel is Cancelled !!!'))
            waybill.message_post(body=_(
                "<h5><strong>Cancel to Draft</strong></h5>"
                "<p><strong>by: </strong> %s <br>"
                "<strong>at: </strong> %s</p") % (
                waybill.user_id.name, fields.Date.today()))
            waybill.state = 'draft'

    @api.multi
    def action_cancel(self):
        for waybill in self:
            if waybill.invoice_paid:
                raise exceptions.ValidationError(
                    _('Could not cancel this waybill because'
                      'the waybill is already paid.'))
            elif waybill.invoice_id and waybill.invoice_id.state != 'cancel':
                raise exceptions.ValidationError(
                    _('You cannot unlink the invoice of this waybill'
                        ' because the invoice is still valid, '
                        'please check it.'))
            else:
                move_obj = self.env['account.move']
                move_id = (move_obj.search(
                    [('id', '=', waybill.move_id.id)]))
                move_count = len(move_id)

                if move_count > 0:
                    move_id.unlink()

                waybill.invoice_id = False
                waybill.state = 'cancel'
                waybill.message_post(body=_(
                    "<h5><strong>Cancelled</strong></h5>"
                    "<p><strong>Cancelled by: </strong> %s <br>"
                    "<strong>Cancelled at: </strong> %s</p") % (
                    waybill.user_id.name, fields.Date.today()))

    @api.depends('supplier_invoice_id')
    def _compute_supplier_invoice_paid(self):
        for rec in self:
            rec.supplier_invoice_paid = False

    @api.multi
    def _amount_to_text(self, amount_total, currency, partner_lang='es_MX'):
        total = str(float(amount_total)).split('.')[0]
        decimals = str(float(amount_total)).split('.')[1]
        currency_type = 'M.N.'
        if partner_lang != 'es_MX':
            total = num2words(float(amount_total)).upper()
        else:
            total = num2words(float(total), lang='es').upper()
        if currency != 'MXN':
            currency_type = 'M.E.'
        else:
            currency = 'PESOS'
        return '%s %s %s/100 %s' % (
            total, currency, decimals or 0.0, currency_type)
