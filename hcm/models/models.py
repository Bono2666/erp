from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HcmPosition(models.Model):
    _name = 'hcm.position'
    _description = 'Position'
    _inherit = ['navigation.mixin']
    _menu_code = 'hcm_position'
    _order = 'name'

    position_id = fields.Char(
        string="Position ID", readonly=True, copy=False,
        default=lambda self: _('New'))
    name = fields.Char(string="Position Name", required=True)
    department_id = fields.Many2one(
        'general.department', string="Department", index=True)
    parent_id = fields.Many2one(
        'hcm.position', string="Superior Position",
        index=True, ondelete='set null')
    child_ids = fields.One2many(
        'hcm.position', 'parent_id', string="Subordinate Positions")
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
    is_edit = fields.Boolean(default=False)

    employee_count = fields.Integer(
        string="Employee Count", compute='_compute_employee_count',
        store=False)
    employee_ids = fields.One2many(
        'hcm.employee', 'position_id', string="Employees")

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for record in self:
            record.employee_count = len(record.employee_ids)

    @api.model
    def create(self, vals):
        if vals.get('position_id', _('New')) == _('New'):
            vals['position_id'] = self.env['ir.sequence'].next_by_code(
                'hcm.position.sequence') or _('New')
        return super().create(vals)

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.parent_id:
                name = f"{record.parent_id.name} / {name}"
            result.append((record.id, name))
        return result


class HcmEmployee(models.Model):
    _name = 'hcm.employee'
    _description = 'Employee'
    _inherit = ['navigation.mixin']
    _menu_code = 'hcm_employee'
    _order = 'employee_id desc'

    # ============================================================
    # TAB 1: Data Karyawan
    # ============================================================

    employee_id = fields.Char(
        string="Employee ID", readonly=True, copy=False,
        default=lambda self: _('New'))
    name = fields.Char(string="Name", required=True)
    nik = fields.Char(string="NIK", required=True)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    company_ref = fields.Many2one(
        'general.company', string="Company")
    location_ref = fields.Many2one(
        'general.location', string="Location")
    division_ref = fields.Many2one(
        'general.division', string="Division")
    department_id = fields.Many2one(
        'general.department', string="Department",
        domain="[('division_id', '=', division_ref)]")
    level_grade_ref = fields.Many2one(
        'general.level_grade', string="Level / Grade")
    position_id = fields.Many2one(
        'hcm.position', string="Position",
        domain="[('department_id', '=', department_id), ('active', '=', True)]")
    manager_id = fields.Many2one(
        'hcm.employee', string="Direct Superior",
        compute='_compute_manager_id', store=True)
    join_date = fields.Date(string="Join Date")
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('resigned', 'Resigned'),
        ('terminated', 'Terminated'),
    ], string="Employee Status", default='active', required=True)
    photo = fields.Binary(string="Photo", attachment=True)
    is_edit = fields.Boolean(default=False)

    # Integration with general.custom_users
    custom_user_id = fields.Many2one(
        'general.custom_users', string="System User",
        ondelete='set null')

    # ============================================================
    # TAB 2: Data Pribadi
    # ============================================================

    # Identity
    place_of_birth = fields.Char(string="Place of Birth")
    date_of_birth = fields.Date(string="Date of Birth")
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string="Gender")
    religion = fields.Selection([
        ('islam', 'Islam'),
        ('christian', 'Christian'),
        ('catholic', 'Catholic'),
        ('hindu', 'Hindu'),
        ('buddha', 'Buddha'),
        ('konghucu', 'Konghucu'),
        ('other', 'Other'),
    ], string="Religion")
    blood_type = fields.Selection([
        ('a', 'A'), ('b', 'B'), ('ab', 'AB'), ('o', 'O'),
    ], string="Blood Type")
    first_name = fields.Char(string="Nama Depan")
    last_name = fields.Char(string="Nama Belakang")
    nationality = fields.Char(string="Kewarganegaraan")
    kk_number = fields.Char(string="No. KK")
    ktp_number = fields.Char(string="No. KTP")
    passport_number = fields.Char(string="No. Passport")
    passport_expiry_date = fields.Date(string="Tanggal Kadaluarsa")
    tax_date = fields.Date(string="Tanggal Pajak")
    height = fields.Float(string="Tinggi Badan")
    weight = fields.Float(string="Berat Badan")
    wear_glasses = fields.Boolean(string="Berkacamata")
    age = fields.Integer(
        string="Usia", compute='_compute_age', store=False)
    npwp = fields.Char(string="NPWP")
    bpjs_kesehatan = fields.Char(string="BPJS Kesehatan")
    bpjs_ketenagakerjaan = fields.Char(string="BPJS Ketenagakerjaan")

    # Address
    address = fields.Text(string="Address")
    country_id = fields.Many2one('general.country', string="Country")
    state_id = fields.Many2one('general.state', string="State")
    city_id = fields.Many2one('general.city', string="City")
    district_id = fields.Many2one('general.district', string="District")
    village_id = fields.Many2one('general.village', string="Village")
    rt = fields.Char(string="RT")
    rw = fields.Char(string="RW")
    postal_code = fields.Char(string="Postal Code")

    # Bank Information
    bank_name = fields.Char(string="Bank Name")
    bank_account_number = fields.Char(string="Account Number")
    bank_account_holder = fields.Char(string="Account Holder")

    # Marriage Information
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], string="Marital Status")
    spouse_name = fields.Char(string="Spouse Name")
    spouse_birth_date = fields.Date(string="Spouse Birth Date")
    children_count = fields.Integer(string="Number of Children")
    marriage_date = fields.Date(string="Tanggal Perkawinan")

    # ============================================================
    # TAB 3: Data Keluarga
    # ============================================================

    family_ids = fields.One2many(
        'hcm.employee.family', 'employee_id', string="Family Members")

    # ============================================================
    # TAB 4: Pendidikan
    # ============================================================

    education_ids = fields.One2many(
        'hcm.employee.education', 'employee_id', string="Formal Education")
    certificate_ids = fields.One2many(
        'hcm.employee.certificate', 'employee_id', string="Certificates")
    training_ids = fields.One2many(
        'hcm.employee.training', 'employee_id', string="Training")

    # ============================================================
    # DOCUMENT REPOSITORY
    # ============================================================

    attachment_ids = fields.Many2many(
        'ir.attachment', string="Documents",
        help="Repository for all employee documents")

    # ============================================================
    # COMPUTED & CONSTRAINTS
    # ============================================================

    _sql_constraints = [
        ('nik_unique', 'unique(nik)',
         'NIK must be unique! An employee with this NIK already exists.'),
    ]

    @api.depends('position_id')
    def _compute_manager_id(self):
        """Compute direct superior based on position hierarchy.
        Finds the nearest employee holding the parent position."""
        for employee in self:
            manager = False
            if employee.position_id and employee.position_id.parent_id:
                # Find an employee who holds the parent position
                manager = self.env['hcm.employee'].search([
                    ('position_id', '=', employee.position_id.parent_id.id),
                    ('status', '=', 'active'),
                ], limit=1)
            employee.manager_id = manager.id if manager else False

    @api.depends('date_of_birth')
    def _compute_age(self):
        """Compute age based on date of birth."""
        from datetime import date
        for employee in self:
            if employee.date_of_birth:
                today = date.today()
                employee.age = today.year - employee.date_of_birth.year - (
                    (today.month, today.day) <
                    (employee.date_of_birth.month, employee.date_of_birth.day)
                )
            else:
                employee.age = 0

    # ============================================================
    # ADDRESS ONCHANGE METHODS (Hierarchical Auto-fill)
    # ============================================================

    @api.onchange('village_id')
    def _onchange_village_id(self):
        """When village is selected, auto-fill district, city, state, country."""
        if self.village_id:
            district = self.village_id.district_ref
            if district:
                self.district_id = district
                city = district.city_ref
                if city:
                    self.city_id = city
                    state = city.state_ref
                    if state:
                        self.state_id = state
                        country = state.country_ref
                        if country:
                            self.country_id = country

    @api.onchange('district_id')
    def _onchange_district_id(self):
        """When district is selected, auto-fill city, state, country."""
        if self.district_id:
            city = self.district_id.city_ref
            if city:
                self.city_id = city
                state = city.state_ref
                if state:
                    self.state_id = state
                    country = state.country_ref
                    if country:
                        self.country_id = country

    @api.onchange('city_id')
    def _onchange_city_id(self):
        """When city is selected, auto-fill state, country."""
        if self.city_id:
            state = self.city_id.state_ref
            if state:
                self.state_id = state
                country = state.country_ref
                if country:
                    self.country_id = country

    @api.onchange('state_id')
    def _onchange_state_id(self):
        """When state is selected, auto-fill country."""
        if self.state_id:
            country = self.state_id.country_ref
            if country:
                self.country_id = country

    # ============================================================
    # ORGANIZATION HIERARCHY ONCHANGE METHODS
    # ============================================================

    @api.onchange('position_id')
    def _onchange_position_id(self):
        """When position is selected, auto-fill department and division."""
        if self.position_id:
            department = self.position_id.department_id
            if department:
                self.department_id = department
                division = department.division_id
                if division:
                    self.division_ref = division

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """When department is selected, auto-fill division."""
        if self.department_id:
            division = self.department_id.division_id
            if division:
                self.division_ref = division

    @api.model
    def create(self, vals):
        if vals.get('employee_id', _('New')) == _('New'):
            vals['employee_id'] = self.env['ir.sequence'].next_by_code(
                'hcm.employee.sequence') or _('New')
        return super().create(vals)

    def action_back(self):
        self.ensure_one()
        return {
            'name': self._description,
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'kanban,tree,form',
            'target': 'main',
            'context': self.env.context,
        }

    def action_view_org_structure(self):
        """Open organization structure view"""
        return {
            'name': _('Organization Structure'),
            'type': 'ir.actions.act_window',
            'res_model': 'hcm.position',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'target': 'current',
            'domain': [('parent_id', '=', False)],
        }


class HcmEmployeeFamily(models.Model):
    _name = 'hcm.employee.family'
    _description = 'Employee Family Member'
    _order = 'id'

    employee_id = fields.Many2one(
        'hcm.employee', string="Employee",
        required=True, ondelete='cascade')
    kk_number = fields.Char(string="KK Number")
    nik = fields.Char(string="NIK")
    name = fields.Char(string="Name", required=True)
    relation = fields.Selection([
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('sibling', 'Sibling'),
        ('other', 'Other'),
    ], string="Relationship", required=True)
    place_of_birth = fields.Char(string="Place of Birth")
    date_of_birth = fields.Date(string="Date of Birth")
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string="Gender")
    last_education = fields.Selection([
        ('sd', 'SD'),
        ('smp', 'SMP'),
        ('sma', 'SMA / SMK'),
        ('d1', 'D1'),
        ('d2', 'D2'),
        ('d3', 'D3'),
        ('s1', 'S1'),
        ('s2', 'S2'),
        ('s3', 'S3'),
    ], string="Last Education")
    phone = fields.Char(string="Phone")


class HcmEmployeeEducation(models.Model):
    _name = 'hcm.employee.education'
    _description = 'Employee Formal Education'
    _order = 'start_year desc'

    employee_id = fields.Many2one(
        'hcm.employee', string="Employee",
        required=True, ondelete='cascade')
    level = fields.Selection([
        ('sd', 'SD'),
        ('smp', 'SMP'),
        ('sma', 'SMA / SMK'),
        ('d1', 'D1'),
        ('d2', 'D2'),
        ('d3', 'D3'),
        ('s1', 'S1'),
        ('s2', 'S2'),
        ('s3', 'S3'),
    ], string="Education Level", required=True)
    institution = fields.Char(string="Institution", required=True)
    major = fields.Char(string="Major")
    start_year = fields.Char(string="Start Year", size=4)
    end_year = fields.Char(string="End Year", size=4)
    gpa = fields.Char(string="GPA")
    document = fields.Binary(string="Diploma/Transcript", attachment=True)

    document_filename = fields.Char(string="Document Filename")


class HcmEmployeeCertificate(models.Model):
    _name = 'hcm.employee.certificate'
    _description = 'Employee Certificate'
    _order = 'date_issued desc'

    employee_id = fields.Many2one(
        'hcm.employee', string="Employee",
        required=True, ondelete='cascade')
    name = fields.Char(string="Certificate Name", required=True)
    issuer = fields.Char(string="Issuer")
    date_issued = fields.Date(string="Date Issued")
    expiry_date = fields.Date(string="Expiry Date")
    certificate_number = fields.Char(string="Certificate Number")
    document = fields.Binary(string="Certificate File", attachment=True)

    document_filename = fields.Char(string="Document Filename")


class HcmEmployeeTraining(models.Model):
    _name = 'hcm.employee.training'
    _description = 'Employee Training'
    _order = 'date_start desc'

    employee_id = fields.Many2one(
        'hcm.employee', string="Employee",
        required=True, ondelete='cascade')
    name = fields.Char(string="Training Name", required=True)
    organizer = fields.Char(string="Organizer")
    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")
    duration_days = fields.Integer(
        string="Duration (Days)", compute='_compute_duration', store=True)
    location = fields.Char(string="Location")
    description = fields.Text(string="Description")
    document = fields.Binary(string="Certificate", attachment=True)

    document_filename = fields.Char(string="Document Filename")

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for record in self:
            if record.date_start and record.date_end:
                delta = record.date_end - record.date_start
                record.duration_days = delta.days + 1
            else:
                record.duration_days = 0
