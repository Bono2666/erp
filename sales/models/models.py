from odoo import models, fields, api


class cust_category(models.Model):
    _name = 'sales.cust_category'
    _description = 'Customer Category'
    _rec_name = 'category_name'

    category_id = fields.Char(string="Category ID", readonly=True)
    category_name = fields.Char(string="Category Name")

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            for v in vals:
                if not v.get('category_id'):
                    v['category_id'] = self.env['ir.sequence'].next_by_code(
                        'sales.cust_category') or '/'
            return super(cust_category, self).create(vals)
        if not vals.get('category_id'):
            vals['category_id'] = self.env['ir.sequence'].next_by_code(
                'sales.cust_category') or '/'
        return super(cust_category, self).create(vals)


class cust_type(models.Model):
    _name = 'sales.cust_type'
    _description = 'Customer Type'
    _rec_name = 'type_name'

    type_id = fields.Char(string="Type ID", readonly=True)
    type_name = fields.Char(string="Type Name")

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            for v in vals:
                if not v.get('type_id'):
                    v['type_id'] = self.env['ir.sequence'].next_by_code(
                        'sales.cust_type') or '/'
            return super(cust_type, self).create(vals)
        if not vals.get('type_id'):
            vals['type_id'] = self.env['ir.sequence'].next_by_code(
                'sales.cust_type') or '/'
        return super(cust_type, self).create(vals)


class cust_area(models.Model):
    _name = 'sales.cust_area'
    _description = 'Customer Area'
    _rec_name = 'area_name'

    area_id = fields.Char(string="Area ID", readonly=True)
    area_name = fields.Char(string="Area Name")

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            for v in vals:
                if not v.get('area_id'):
                    v['area_id'] = self.env['ir.sequence'].next_by_code(
                        'sales.cust_area') or '/'
            return super(cust_area, self).create(vals)
        if not vals.get('area_id'):
            vals['area_id'] = self.env['ir.sequence'].next_by_code(
                'sales.cust_area') or '/'
        return super(cust_area, self).create(vals)


class customer(models.Model):
    _name = 'sales.customer'
    _description = 'Customer'
    _rec_name = 'customer_name'

    customer_id = fields.Char(string="Customer ID", readonly=True)
    customer_name = fields.Char(string="Customer Name")
    address = fields.Text(string="Address")
    country = fields.Many2one(
        comodel_name='general.country', string='Country', ondelete='set null', index=True)
    state = fields.Many2one(
        comodel_name='general.state', string='State', ondelete='set null', index=True)
    city = fields.Many2one(
        comodel_name='general.city', string='City', ondelete='set null', index=True)
    district = fields.Many2one(
        comodel_name='general.district', string='District', ondelete='set null', index=True)
    sales_code = fields.Many2one(
        comodel_name='employees.employees', string='Sales', ondelete='set null', index=True,
        domain=[('sales_code', '!=', False)])
    npwp = fields.Char(string="NPWP")
    cust_category = fields.Many2one(
        comodel_name='sales.cust_category', string='Customer Category', ondelete='set null', index=True)
    cust_type = fields.Many2one(
        comodel_name='sales.cust_type', string='Customer Type', ondelete='set null', index=True)
    cust_area = fields.Many2one(
        comodel_name='sales.cust_area', string='Customer Area', ondelete='set null', index=True)
    price_condition = fields.Many2one(
        comodel_name='sales.price_condition', string='Price Condition', ondelete='set null', index=True)
    payment_terms = fields.Many2one(
        comodel_name='sales.payment_terms', string='Payment Terms', ondelete='set null', index=True)
    contact_name = fields.Char(string="Contact Name")
    telephone = fields.Char(string="Telephone")
    email = fields.Char(string="Email")
    website = fields.Char(string="Website")
    ship_to_ids = fields.One2many(
        'sales.ship_to', 'customer_id', string="Ship To Addresses")

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            for v in vals:
                if not v.get('customer_id'):
                    v['customer_id'] = self.env['ir.sequence'].next_by_code(
                        'sales.customer') or '/'
            return super(customer, self).create(vals)
        if not vals.get('customer_id'):
            vals['customer_id'] = self.env['ir.sequence'].next_by_code(
                'sales.customer') or '/'
        return super(customer, self).create(vals)


class ship_to(models.Model):
    _name = 'sales.ship_to'
    _description = 'Ship To'
    _rec_name = 'ship_name'

    ship_id = fields.Char(string="Ship ID", readonly=True)
    ship_name = fields.Char(string="Ship Name")
    customer_id = fields.Many2one(
        comodel_name='sales.customer', string='Customer', ondelete='cascade', index=True)
    address = fields.Text(string="Address")
    country = fields.Many2one(
        comodel_name='general.country', string='Country', ondelete='set null', index=True)
    state = fields.Many2one(
        comodel_name='general.state', string='State', ondelete='set null', index=True)
    city = fields.Many2one(
        comodel_name='general.city', string='City', ondelete='set null', index=True)
    district = fields.Many2one(
        comodel_name='general.district', string='District', ondelete='set null', index=True)

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            for v in vals:
                if not v.get('ship_id'):
                    v['ship_id'] = self.env['ir.sequence'].next_by_code(
                        'sales.ship_to') or '/'
            return super(ship_to, self).create(vals)
        if not vals.get('ship_id'):
            vals['ship_id'] = self.env['ir.sequence'].next_by_code(
                'sales.ship_to') or '/'
        return super(ship_to, self).create(vals)


class product_type(models.Model):
    _name = 'sales.product_type'
    _description = 'Product Type'

    name = fields.Char(string='Product Type')


class product_unit(models.Model):
    _name = 'sales.product_unit'
    _description = 'Product Unit'
    _rec_name = 'uom'

    uom = fields.Char(string='Unit of Measure')
    qty = fields.Integer(string='Qty')
    base_uom = fields.Char(string='Base UoM')
    base_qty = fields.Integer(string='Base Qty')


class products(models.Model):
    _name = 'sales.products'
    _description = 'Products'
    _rec_name = 'product_name'

    product_id = fields.Char(string="Product ID", readonly=True)
    product_name = fields.Char(string="Product Name")
    product_type = fields.Many2one(
        comodel_name='sales.product_type', string='Product Type')
    product_unit = fields.Many2one(
        comodel_name='sales.product_unit', string='Product Unit')

    image = fields.Binary(string="Image")

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            for v in vals:
                if not v.get('product_id'):
                    v['product_id'] = self.env['ir.sequence'].next_by_code(
                        'sales.products') or '/'
            return super(products, self).create(vals)
        if not vals.get('product_id'):
            vals['product_id'] = self.env['ir.sequence'].next_by_code(
                'sales.products') or '/'
        return super(products, self).create(vals)


class price_condition(models.Model):
    _name = 'sales.price_condition'
    _description = 'Price Condition'
    _rec_name = 'price_name'

    price_id = fields.Char(string="Price ID", readonly=True)
    price_name = fields.Char(string="Price Name")
    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")
    product_ids = fields.One2many(
        'sales.price_condition_product', 'price_id', string="Products")
    customer_ids = fields.One2many(
        'sales.price_condition_customer', 'price_id', string="Customers")

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            for v in vals:
                if not v.get('price_id'):
                    v['price_id'] = self.env['ir.sequence'].next_by_code(
                        'sales.price_condition') or '/'
            return super(price_condition, self).create(vals)
        if not vals.get('price_id'):
            vals['price_id'] = self.env['ir.sequence'].next_by_code(
                'sales.price_condition') or '/'
        return super(price_condition, self).create(vals)


class price_condition_product(models.Model):
    _name = 'sales.price_condition_product'
    _description = 'Price Condition - Product'

    price_id = fields.Many2one(
        comodel_name='sales.price_condition', string='Price Condition', ondelete='cascade', index=True)
    product_id = fields.Many2one(
        comodel_name='sales.products', string='Product', ondelete='set null', index=True)
    price = fields.Float(string="Price")


class price_condition_customer(models.Model):
    _name = 'sales.price_condition_customer'
    _description = 'Price Condition - Customer'

    price_id = fields.Many2one(
        comodel_name='sales.price_condition', string='Price Condition', ondelete='cascade', index=True)
    customer_id = fields.Many2one(
        comodel_name='sales.customer', string='Customer', ondelete='set null', index=True)


class account_type(models.Model):
    _name = 'sales.account_type'
    _description = 'Account Type'

    name = fields.Char(string='Account Type', required=True)


class payment_terms(models.Model):
    _name = 'sales.payment_terms'
    _description = 'Payment Terms'
    _rec_name = 'sales_text'

    payment_terms_id = fields.Char(string="Payment Terms ID", readonly=True)
    sales_text = fields.Char(string="Sales Text")
    account_type = fields.Many2many(
        'sales.account_type', string="Account Type")
    baseline_date = fields.Selection([
        ('doc', 'Document Date'),
        ('post', 'Posting Date'),
        ('entry', 'Entry Date')
    ], string="Default for Baseline Date")
    payment_terms_ids = fields.One2many(
        'sales.payment_terms_detail', 'payment_terms_id', string="Payment Terms")

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            for v in vals:
                if not v.get('payment_terms_id'):
                    v['payment_terms_id'] = self.env['ir.sequence'].next_by_code(
                        'sales.payment_terms') or '/'
            return super(payment_terms, self).create(vals)
        if not vals.get('payment_terms_id'):
            vals['payment_terms_id'] = self.env['ir.sequence'].next_by_code(
                'sales.payment_terms') or '/'
        return super(payment_terms, self).create(vals)


class payment_terms_detail(models.Model):
    _name = 'sales.payment_terms_detail'
    _description = 'Payment Terms - Detail'

    payment_terms_id = fields.Many2one(
        comodel_name='sales.payment_terms', string='Payment Terms ID', ondelete='cascade', index=True)
    percentage = fields.Float(string="Percentage")
    no_of_days = fields.Integer(string="No of Days")
    explanation = fields.Char(string="Explanation")
