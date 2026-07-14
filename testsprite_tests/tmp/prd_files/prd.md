# ERP KSI — Product Requirements Document

> **Last updated:** 2026-07-12
> **Stack:** Odoo 17 (Python) + OWL Framework (JavaScript) + PostgreSQL

---

## 1. System Overview

ERP KSI is a modular enterprise resource planning system built on Odoo 17. It provides human capital management (HCM), sales management with multi-level approval workflows, address master data, role-based access control, and a home dashboard — all with a custom form edit/save UX pattern.

### 1.1 Modules

| Module             | Dependencies                                         | Purpose                                                      |
| ------------------ | ---------------------------------------------------- | ------------------------------------------------------------ |
| `disable_autosave` | `base`                                               | Disables Odoo auto-save; Cancel button handler               |
| `general`          | `base`, `disable_autosave`                           | Master data, user management, RBAC, home dashboard           |
| `hcm`              | `base`, `general`, `disable_autosave`                | Positions, employees, organization chart                     |
| `sales`            | `base`, `general`, `hcm`, `disable_autosave`, `mail` | Quotations → sales orders → invoices → payments → deliveries |
| `user_management`  | `base`, `general`, `hcm`, `disable_autosave`         | User & access rights management UI                           |

---

## 2. Form Edit/Save Pattern (NavigationMixin)

### 2.1 Aturan Dasar

Setiap form master-data mengikuti aturan berikut:

1. **Default State = View Mode** — Semua field readonly saat melihat record yang sudah ada
2. **New Record = Edit Mode** — Semua field langsung editable saat membuat record baru
3. **Edit Button** — User harus klik tombol **Edit** untuk mengubah record yang sudah ada
4. **Save Button** — Klik **Save** untuk menyimpan perubahan dan kembali ke View Mode
5. **Cancel Button** — Klik **Cancel** untuk membatalkan perubahan dan kembali ke View Mode

### 2.2 Cara Kerja (Auto-Injection via `get_views()`)

Semua form master-data yang memiliki `<field name="is_edit"/>` di `<header>` akan otomatis di-inject `readonly="not is_edit and id"` ke setiap field di dalam `<sheet>`.

Logic ini ada di `general/models/models.py` → `NavigationMixin.get_views()`.

### 2.3 Kondisi `is_edit` Expression

| State      | `id`  | `is_edit` | `not is_edit and id`              | Field        |
| ---------- | ----- | --------- | --------------------------------- | ------------ |
| New record | False | False     | `not False and False` = **False** | **Editable** |
| View mode  | True  | False     | `not False and True` = **True**   | **Readonly** |
| Edit mode  | True  | True      | `not True and True` = **False**   | **Editable** |

### 2.4 Field yang TIDAK di-inject readonly

| Kategori                              | Keterangan                                          |
| ------------------------------------- | --------------------------------------------------- |
| Field dengan `readonly` di XML        | Misal workflow forms: `readonly="state != 'draft'"` |
| Field dengan `readonly=True` di model | Misal ID field: `employee_id`, `country_id`, dll.   |
| Computed field tanpa inverse          | Misal `manager_id`, `employee_count`, dll.          |
| System fields                         | `id`, `is_edit`, `user_can_*`, `model_description`  |
| Field di dalam `<tree>`               | Inline one2many tree rows                           |
| Field di dalam embedded `<form>`      | Sub-form milik one2many field                       |
| Field invisible                       | Field dengan attribute `invisible`                  |

### 2.5 Membuat Form Baru — Checklist

1. Model wajib inherit `navigation.mixin` dan punya `is_edit = fields.Boolean(default=False)`
2. Form XML wajib memiliki header buttons (Back, Edit, Save, Cancel, Delete)
3. Field TIDAK PERLU ditambahkan `readonly` manual — auto-injection yang handle
4. Field yang harus selalu readonly: gunakan `readonly=True` di model (preferred), atau `readonly` di XML

### 2.6 Workflow Forms (Pengecualian)

Form dengan workflow state-based (sales order, invoice, payment, delivery) **tidak** menggunakan pattern standar. Mereka menggunakan `readonly` berbasis `state`:

```xml
<field name="order_line_ids" readonly="state in ['cancel', 'wait_approval'] or (not is_edit and id)"/>
```

---

## 3. Module: `disable_autosave`

**Purpose:** Disable Odoo's auto-save on form blur and handle Cancel button behavior.

### 3.1 Features

- Prevents automatic save when clicking outside a form field
- Custom JavaScript (`disable_autosave.js`) handles `.discard-new` and `.discard-edit` CSS class buttons for cancel behavior
- CSS styling adjustments

---

## 4. Module: `general` — Master Data & Core

### 4.1 NavigationMixin (`general/models/models.py`)

Abstract model (`navigation.mixin`) inherited by all master-data models. Provides:

| Feature              | Method/Field                                                         | Description                                                   |
| -------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------- |
| Auto-inject readonly | `get_views()`                                                        | Injects `readonly="not is_edit and id"` to form fields        |
| CRUD actions         | `action_back()`, `action_edit()`, `action_save()`, `action_delete()` | Standard navigation actions                                   |
| Permissions          | `user_can_read/create/update/delete`                                 | Computed from `general.auth` records                          |
| Password action      | `action_password()`                                                  | Opens change password wizard for custom users                 |
| System field sync    | `action_save()`                                                      | Syncs `name`, `login` to `res.users` when saving custom_users |

### 4.2 Address Hierarchy

| Model              | Table     | Key Fields                                              | Menu Code  |
| ------------------ | --------- | ------------------------------------------------------- | ---------- |
| `general.country`  | Countries | `country_id`, `country_name`                            | `country`  |
| `general.state`    | States    | `state_id`, `state_name`, `country_ref` → country       | `state`    |
| `general.city`     | Cities    | `city_id`, `city_name`, `state_ref` → state             | `city`     |
| `general.district` | Districts | `district_id`, `district_name`, `city_ref` → city       | `district` |
| `general.village`  | Villages  | `village_id`, `village_name`, `district_ref` → district | `village`  |

All inherit `navigation.mixin`. IDs auto-generated via sequences.

#### 4.2.1 Aturan Hirarki Alamat (Address Hierarchy Rules)

**Prinsip Dasar:**
Setiap field dalam hierarki alamat bersifat **dependent** — dropdown child hanya menampilkan data yang relevan dengan parent yang dipilih. Jika parent kosong, dropdown child menampilkan **semua data**.

**Hierarki:**

```
Country → State → City → District → Village
```

**Aturan Domain (Filter Dropdown):**

| Field      | Domain                              | Kondisi                                          |
| ---------- | ----------------------------------- | ------------------------------------------------ |
| `state`    | `[('country_ref', '=', country)]`   | Jika `country` kosong → tampilkan semua state    |
| `city`     | `[('state_ref', '=', state)]`       | Jika `state` kosong → tampilkan semua city       |
| `district` | `[('city_ref', '=', city)]`         | Jika `city` kosong → tampilkan semua district    |
| `village`  | `[('district_ref', '=', district)]` | Jika `district` kosong → tampilkan semua village |

**Implementasi Domain di XML:**

```xml
domain="[('country_ref', '=', country_id)] if country_id else []"
```

Pattern: `[(field, '=', parent)] if parent else []`

**Aturan Auto-Fill (Onchange Methods):**

Ketika user memilih data pada level mana pun, semua parent field otomatis terisi:

| Trigger          | Auto-fill Sequence                  |
| ---------------- | ----------------------------------- |
| Village dipilih  | → District → City → State → Country |
| District dipilih | → City → State → Country            |
| City dipilih     | → State → Country                   |
| State dipilih    | → Country                           |

**Implementasi di Python:**

```python
@api.onchange('village_id')
def _onchange_village_id(self):
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
```

**Lokasi Implementasi:**

| Form                     | Module | File                     | Fields                                                           |
| ------------------------ | ------ | ------------------------ | ---------------------------------------------------------------- |
| Employee (Personal Data) | hcm    | `hcm/models/models.py`   | `country_id`, `state_id`, `city_id`, `district_id`, `village_id` |
| Customer                 | sales  | `sales/models/models.py` | `country`, `state`, `city`, `district`                           |
| Ship-To Address          | sales  | `sales/models/models.py` | `country`, `state`, `city`, `district`                           |

**Catatan Penting:**

- Customer dan Ship-To tidak memiliki field `village` — hierarki dimulai dari District
- Field names berbeda antara models: HCM menggunakan suffix `_id` (misal `country_id`), Sales menggunakan nama field langsung (misal `country`)
- Semua onchange methods harus diimplementasikan di Python model, bukan di XML

### 4.3 Organization Master Data

| Model                 | Table          | Key Fields                                                                         | Menu Code     |
| --------------------- | -------------- | ---------------------------------------------------------------------------------- | ------------- |
| `general.company`     | Companies      | `company_id`, `company_name`                                                       | `company`     |
| `general.location`    | Locations      | `location_id`, `location_name`                                                     | `location`    |
| `general.division`    | Divisions      | `division_id`, `division_name`, `department_ids` (o2m)                             | `division`    |
| `general.department`  | Departments    | `department_id`, `department_name`, `division_id` → division, `position_ids` (o2m) | `department`  |
| `general.position`    | Position (ref) | `position_id`, `position_name`, `department_id` → department                       | `position`    |
| `general.level_grade` | Levels/Grades  | `level_id`, `level_name`                                                           | `level_grade` |

#### 4.3.1 Aturan Hirarki Organisasi (Organization Hierarchy Rules)

**Prinsip Dasar:**
Sama seperti hirarki alamat — dropdown child hanya menampilkan data yang relevan dengan parent. Jika parent kosong, dropdown child menampilkan **semua data**.

**Hierarki:**
```
Division → Department → Position
```

**Aturan Domain (Filter Dropdown):**

| Field | Domain | Kondisi |
|-------|--------|---------|
| `department_id` | `[('division_id', '=', division_ref)]` | Jika `division_ref` kosong → tampilkan semua department |
| `position_id` | `[('department_id', '=', department_id)]` | Jika `department_id` kosong → tampilkan semua position |

**Implementasi di XML:**
```xml
<field name="department_id" domain="[('division_id', '=', division_ref)] if division_ref else []"/>
<field name="position_id" domain="[('department_id', '=', department_id)] if department_id else []"/>
```

**Aturan Auto-Fill (Onchange Methods):**

Ketika user memilih data pada level mana pun, semua parent field otomatis terisi:

| Trigger | Auto-fill Sequence |
|---------|-------------------|
| Position dipilih | → Department → Division |
| Department dipilih | → Division |

**Implementasi di Python:**
```python
@api.onchange('position_id')
def _onchange_position_id(self):
    if self.position_id:
        department = self.position_id.department_id
        if department:
            self.department_id = department
            division = department.division_id
            if division:
                self.division_ref = division

@api.onchange('department_id')
def _onchange_department_id(self):
    if self.department_id:
        division = self.department_id.division_id
        if division:
            self.division_ref = division
```

**Lokasi Implementasi:**

| Form | Module | File |
|------|--------|------|
| Employee (Organization) | hcm | `hcm/models/models.py` |

**Catatan Penting:**
- `division_ref` adalah field top-level — tidak ada parent di atasnya
- `department_id` memiliki `division_id` sebagai foreign key
- `position_id` memiliki `department_id` sebagai foreign key
- Relationship: `general.position` → `general.department` → `general.division`

### 4.4 RBAC — User & Access Management

#### Models

| Model                  | Description                                                                                                                                     |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `general.custom_users` | Custom user records linked to `res.users`. Fields: name, login, password, position, photo, menu access (o2m → general.auth), related `user_id`  |
| `general.auth`         | Per-user-per-menu access rights: can_create, can_update, can_delete, can_submit, can_send, can_confirm, can_invoicing, can_receive, can_billing |
| `general.menu`         | Menu registry with `menu_id`, `menu_name`, `parent_menu`, `is_parent`                                                                           |

#### How RBAC Works

1. Each `general.custom_users` record creates a corresponding `res.users` record
2. User gets `general.auth` records per menu, controlling CRUD and workflow actions
3. Admin (`base.group_system`) always has full access — no restrictions
4. Non-admin users see only menus they have `general.auth` records for
5. Menu visibility is enforced via `ir.ui.menu` → `restrict_user_ids` (hidden menus)

#### Key Methods

| Method                                   | Description                                                                         |
| ---------------------------------------- | ----------------------------------------------------------------------------------- |
| `ResUsers._refresh_custom_menu_access()` | Rebuilds menu visibility: auto-generates parent menu auth, hides unauthorized menus |
| `ResUsers._update_last_login()`          | Called on login; triggers menu access refresh                                       |
| `IrUiMenu._filter_visible_menus()`       | Filters out menus restricted for current user                                       |

#### Password Wizards

| Model                          | Description                                                   |
| ------------------------------ | ------------------------------------------------------------- |
| `general.password`             | Admin changes any user's password                             |
| `general.password_preferences` | User changes own password (2-step: verify old → set new)      |
| `general.preferences`          | User profile: change name, photo, and trigger password change |

### 4.5 Home Dashboard

Model: `general.home`

Computes visibility of module cards (HCM, Sales, Configuration) based on user's menu access. Actions navigate to module root menus via `menu_id` URL.

### 4.6 Sequences

Auto-generated IDs use `ir.sequence` records defined in `data/sequence.xml` for all master data models.

---

## 5. Module: `hcm` — Human Capital Management

### 5.1 Position (`hcm.position`)

| Field            | Type                          | Notes                               |
| ---------------- | ----------------------------- | ----------------------------------- |
| `position_id`    | Char (readonly)               | Auto-generated from sequence        |
| `name`           | Char (required)               | Position name                       |
| `department_id`  | Many2one → general.department |                                     |
| `parent_id`      | Many2one → hcm.position       | Self-referencing hierarchy          |
| `child_ids`      | One2many → hcm.position       | Subordinate positions               |
| `description`    | Text                          |                                     |
| `active`         | Boolean                       | Soft-delete flag                    |
| `employee_count` | Integer (computed)            | Count of employees in this position |
| `employee_ids`   | One2many → hcm.employee       |                                     |

Inherits `navigation.mixin`. Uses `name_get()` to display parent/child naming.

### 5.2 Employee (`hcm.employee`)

**Tab 1 — Employee Data:** NIK, name, phone, email, company, location, division, department, level/grade, position, manager (computed from position hierarchy), join date, status (active/inactive/resigned/terminated), photo, system user link

**Tab 2 — Personal Data:** Identity (first/last name, POB, DOB, age, gender, religion, blood type, nationality), tax IDs (NPWP, BPJS), address (country→state→city→district→village, RT/RW, postal code), bank info, marriage info (status, spouse, children)

**Tab 3 — Family:** `hcm.employee.family` (KK, NIK, name, relation, POB, DOB, gender, education, phone)

**Tab 4 — Education:** Three sub-tables:

- `hcm.employee.education` (level, institution, major, years, GPA)
- `hcm.employee.certificate` (name, issuer, dates, number)
- `hcm.employee.training` (name, organizer, dates, duration, location)

**Documents:** `attachment_ids` (m2m → ir.attachment) for document repository

**Computed Fields:**

- `manager_id` — finds employee holding parent position
- `age` — computed from `date_of_birth`

Inherits `navigation.mixin`.

### 5.3 Organization Structure Chart

| Feature           | Detail                                                                       |
| ----------------- | ---------------------------------------------------------------------------- |
| **Technology**    | OWL Component (`OrgStructure`) + d3-org-chart v2.6.0                         |
| **Entry Point**   | Client action `hcm_org_structure`, menu "Organization Structure"             |
| **Data Source**   | Active positions + active employees via ORM                                  |
| **Visualization** | Flat array (id/parentId) rendered as interactive org chart                   |
| **Node Content**  | Position name, department, employee count, employee names                    |
| **Interactions**  | Scroll zoom, drag pan, click expand/collapse                                 |
| **Dependencies**  | d3.v7.min.js, d3-flextree v2.1.2, d3-org-chart v2.6.0 (all CDN)              |
| **Files**         | `hcm/static/src/js/org_structure.js`, `hcm/static/src/xml/org_structure.xml` |

---

## 6. Module: `sales` — Sales Management

### 6.1 Customer Master Data

| Model                 | Description         | Key Fields                                                                                                                                                                                                                   |
| --------------------- | ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sales.cust_category` | Customer Categories | `category_id`, `category_name`                                                                                                                                                                                               |
| `sales.cust_type`     | Customer Types      | `type_id`, `type_name`                                                                                                                                                                                                       |
| `sales.cust_area`     | Customer Areas      | `area_id`, `area_name`                                                                                                                                                                                                       |
| `sales.customer`      | Customers           | `customer_id`, `customer_name`, address hierarchy (country→state→city→district), postal code, NPWP, salesperson (→ hcm.employee), category/type/area, price conditions (m2m), payment terms, contact info, ship-to addresses |
| `sales.ship_to`       | Ship-To Addresses   | `ship_id`, `ship_name`, address, linked to customer                                                                                                                                                                          |

Customers auto-create linked `res.partner` records. Price conditions auto-sync based on category matching.

### 6.2 Product Master Data

| Model                    | Description        | Key Fields                                                                                                                                                                |
| ------------------------ | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sales.product_type`     | Product Types      | `name`                                                                                                                                                                    |
| `sales.product_category` | Product Categories | `category_name`                                                                                                                                                           |
| `sales.product_unit`     | Units of Measure   | `uom`, `qty`, `base_uom`, `base_qty`                                                                                                                                      |
| `sales.products`         | Products           | `product_id`, `product_name`, barcode, type/category/unit, `base_price`, `price`, `customer_tax` (→ taxes), `stock`, `qty_reserved_sale` (computed from open SO), `image` |
| `sales.taxes`            | Taxes              | `name`, `tax_percentage`, `default_tax` (only one)                                                                                                                        |

**Stock booking:** Products track `qty_reserved_sale` — quantity booked on open (non-cancelled) sales orders. This is used for Indent detection.

### 6.3 Price Conditions

Model: `sales.price_condition`

Complex pricing rules with priority-based matching:

| Dimension      | Values                                        | Priority               |
| -------------- | --------------------------------------------- | ---------------------- |
| Product scope  | All (3), Category (2), Specific Products (1)  | Higher = less specific |
| Customer scope | All (3), Category (2), Specific Customers (1) | Higher = less specific |

**Computation modes:** Fixed Price or Discount (%)

**Sync behavior:** When a price condition is created/updated, it auto-syncs to matching customers via `customer_price_condition_rel` m2m table.

### 6.4 Payment Terms

| Model                        | Description                                             |
| ---------------------------- | ------------------------------------------------------- |
| `sales.account_type`         | Account types (e.g., Customer, Supplier)                |
| `sales.payment_terms`        | Payment term headers with early discount, baseline date |
| `sales.payment_terms_detail` | Installment lines: percentage, no_of_days               |

Features: Example preview calculation, HTML notes sync from sales text.

### 6.5 Sales Orders (`sales.sales_order`)

#### State Machine

```
draft → wait_approval → approved → sent → sale → (invoiced)
  ↓         ↓              ↓         ↓       ↓
cancel    cancel          cancel    cancel  cancel

sale_draft → wait_approval → approved → sale
```

Two entry points:

- **Quotations** (`is_quotation=True`): `draft → wait_approval → approved → sent → sale`
- **Sales Orders** (`is_quotation=False`): `sale_draft → wait_approval → approved → sale`

#### Approval Workflow

**Multi-level sequential approval** based on `sales.sales_approval_matrix`:

1. When an SO line discount exceeds `base_discount` OR total amount exceeds matrix thresholds, approval is required
2. An approval log (`sales.sales_approval_log`) is generated with one entry per matrix level (sorted by sequence)
3. Approvers act in sequence: approve, revise, return, or reject
4. Approver permissions are computed per-user from the matrix

**Available actions per approver (from matrix):**

- **Approve** — advances to next approver or fully approves
- **Revise** — sends back with message, resets approval chain
- **Return** — sends back; if `receive_return` is set on a lower sequence, that approver re-approves
- **Reject** — cancels the SO

**Notification:** Email sent to each pending approver via mail template.

#### Invoice Integration

Invoices created from confirmed (`sale`) sales orders:

- **Regular Invoice** — full invoice with all SO lines
- **Down Payment (Percentage)** — invoice for % of total
- **Down Payment (Fixed)** — invoice for fixed amount

Invoice status tracked: `no`, `to_invoice`, `invoiced`

### 6.6 Invoices (`sales.invoice`)

#### State: `draft → posted → (credit note)`, `draft → cancel`

| Feature                 | Detail                                            |
| ----------------------- | ------------------------------------------------- |
| Types                   | Regular, Down Payment (%), Down Payment (Fixed)   |
| Document types          | Invoice, Credit Note                              |
| Automatic journal items | Receivable, Revenue, Tax — auto-generated on post |
| Payment terms display   | Installment schedule preview                      |
| Amount tracking         | Untaxed, Tax, Total; Paid, Due                    |

#### Credit Notes

- Created from posted invoices via wizard
- Reverses original invoice lines
- Generates opposite-sign journal items

### 6.7 Payments (`sales.payment`)

#### State: `draft → posted`, `draft → cancel`

| Feature          | Detail                                     |
| ---------------- | ------------------------------------------ |
| Methods          | Manual, Bank Transfer, Check, Cash         |
| Journal entries  | Debit Cash/Bank, Credit Account Receivable |
| Invoice tracking | Payment state: not_paid → partial → paid   |

Payment wizard pre-fills amount due and validates against remaining balance.

### 6.8 Deliveries (`sales.delivery`)

#### State: `draft → done`, `draft → cancel`

Tracks physical delivery of goods against sales order lines. Captures ordered quantity vs. delivered quantity.

### 6.9 Email Integration

| Template                                | Purpose                                     |
| --------------------------------------- | ------------------------------------------- |
| `email_template_compressor_quotation`   | Send quotation by email                     |
| `email_template_sales_approval_request` | Notify next approver                        |
| `email_template_sales_invoice`          | Send invoice by email (with PDF attachment) |

Uses `sales.customer` → `partner_id` for recipient resolution. Pre-fills customers in mail compose wizard.

### 6.10 Terms & Conditions

Model: `sales.terms_and_conditions` — auto-populated as default `note` on new sales orders.

---

## 7. Module: `user_management`

Provides UI views for managing `general.custom_users` and `general.auth` records. Depends on `general` for the underlying models.

---

## 8. Security & Access Control

### 8.1 Authentication

- Standard Odoo `res.users` authentication
- Custom users (`general.custom_users`) are linked 1:1 with `res.users`
- On login, `_update_last_login()` triggers menu access refresh

### 8.2 Authorization (RBAC)

**Admin (`base.group_system`):** Full unrestricted access to all menus and actions.

**Non-admin users:**

- Menu visibility controlled by `ir.ui.menu.restrict_user_ids`
- CRUD permissions per menu via `general.auth` records
- Workflow permissions: can_submit, can_send, can_confirm, can_invoicing per menu
- Access enforced in:
  - `NavigationMixin.get_views()` — hides Create button if no `can_create`
  - `NavigationMixin._compute_custom_permissions()` — sets user*can*\* fields
  - Individual action methods (e.g., `_check_cancel_order_access()`, `_check_invoicing_access()`)

### 8.3 CSV Access Rights

Each module defines `security/ir.model.access.csv` for model-level CRUD access control.

---

## 9. Frontend Architecture

### 9.1 Framework

- **OWL (Odoo Web Library)** v2 — component-based UI
- **Bootstrap** CSS utilities for layout
- **Font Awesome** for icons

### 9.2 JavaScript Components

| Component          | Module           | File                                                 | Purpose                        |
| ------------------ | ---------------- | ---------------------------------------------------- | ------------------------------ |
| `OrgStructure`     | hcm              | `hcm/static/src/js/org_structure.js`                 | Interactive organization chart |
| `disable_autosave` | disable_autosave | `disable_autosave/static/src/js/disable_autosave.js` | Cancel button behavior         |

### 9.3 External Libraries (CDN)

| Library      | Version | Used By            |
| ------------ | ------- | ------------------ |
| d3.js        | v7      | Org chart          |
| d3-flextree  | v2.1.2  | Org chart (layout) |
| d3-org-chart | v2.6.0  | Org chart          |

### 9.4 Kanban View Standard Style

Semua kanban view dengan foto/gambar harus mengikuti standar styling berikut:

#### 9.4.1 Struktur HTML

```xml
<div class="oe_kanban_card oe_kanban_global_click o_kanban_record_has_image_fill">
  <div class="o_kanban_image">
    <img t-att-src="kanban_image('model', 'field', record.id.raw_value)" 
         alt="Photo" class="o_image_64_cover"/>
  </div>
  <div class="oe_kanban_details">
    <!-- content here -->
  </div>
</div>
```

#### 9.4.2 CSS Standard

```css
.o_kanban_record_has_image_fill {
    display: flex !important;
    padding: 0 !important;
}

.o_kanban_record_has_image_fill .o_kanban_image {
    flex: 0 0 auto !important;
    width: 100px !important;
    min-height: 100px !important;
    height: 100% !important;
    margin: 0 !important;
    display: flex !important;
}

.o_kanban_record_has_image_fill .o_kanban_image img {
    width: 100% !important;
    height: 100% !important;
    min-height: 100px !important;
    object-fit: cover !important;
    border-radius: 0 !important;
}

.o_kanban_record_has_image_fill .oe_kanban_details {
    flex: 1 !important;
    padding: 8px 12px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
}
```

#### 9.4.3 Aturan

| Aturan | Keterangan |
|--------|------------|
| **Full Height** | Foto harus mengisi tinggi penuh card (tidak ada padding atas/bawah) |
| **Left Aligned** | Foto selalu di posisi kiri card |
| **Object Fit: Cover** | Foto menggunakan `object-fit: cover` agar mengisi area tanpa distorsi |
| **Fixed Width** | Lebar foto tetap 100px, tidak ikut lebar card |
| **Min Height** | Minimum tinggi 100px untuk konsistensi |
| **No Border Radius** | Foto tanpa rounded corners (sharp edges) |
| **Flex Layout** | Card menggunakan flexbox: foto kiri (fixed), details kanan (flex: 1) |

#### 9.4.4 Penerapan

| Module | Model | File CSS |
|--------|-------|----------|
| hcm | `hcm.employee` | `hcm/static/src/css/employee_kanban.css` |

Untuk module baru yang memiliki kanban view dengan foto, buat file CSS baru dan ikuti standar di atas.

---

## 10. Data Model Overview

```
general
├── general.country
├── general.state → country
├── general.city → state
├── general.district → city
├── general.village → district
├── general.company
├── general.location
├── general.division
├── general.department → division
├── general.position → department
├── general.level_grade
├── general.menu
├── general.custom_users → res.users
├── general.auth → custom_users + menu
├── general.home

hcm
├── hcm.position (self-referencing hierarchy) → department
├── hcm.employee → position, department, division, location, company, level_grade
├── hcm.employee.family → employee
├── hcm.employee.education → employee
├── hcm.employee.certificate → employee
├── hcm.employee.training → employee

sales
├── sales.cust_category
├── sales.cust_type
├── sales.cust_area
├── sales.customer → category, type, area, salesperson (hcm.employee), payment_terms
├── sales.ship_to → customer
├── sales.product_type
├── sales.product_category
├── sales.product_unit
├── sales.products → type, category, unit, customer_tax
├── sales.taxes
├── sales.price_condition (m2m with customer/product)
├── sales.account_type
├── sales.payment_terms → account_type
├── sales.payment_terms_detail → payment_terms
├── sales.terms_and_conditions
├── sales.sales_approval_matrix → hcm.employee (approver)
├── sales.sales_order → customer, payment_terms, salesperson (hcm.employee)
├── sales.sales_order_line → sales_order, product, taxes
├── sales.sales_approval_log → sales_order
├── sales.invoice → sales_order, customer, payment_terms
├── sales.invoice.line → invoice, product, tax
├── sales.invoice.journal.item → invoice
├── sales.payment → invoice, customer
├── sales.payment.journal.item → payment
├── sales.delivery → sales_order, customer
├── sales.delivery.line → delivery, sales_order_line, product
```

---

## 11. Key File Locations

| File                                                   | Purpose                                                                                 |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `general/models/models.py`                             | NavigationMixin (auto-injection, actions, permissions), all master data models, RBAC    |
| `general/views/views.xml`                              | Form/tree views for all general models                                                  |
| `general/data/menu.xml`                                | Menu structure for master data                                                          |
| `general/data/home.xml`                                | Home dashboard view                                                                     |
| `general/data/sequence.xml`                            | ID sequences                                                                            |
| `hcm/models/models.py`                                 | Position, Employee, Family, Education, Certificate, Training models                     |
| `hcm/views/views.xml`                                  | Position/Employee form views, actions, menus                                            |
| `hcm/views/templates.xml`                              | Position org tree view                                                                  |
| `hcm/static/src/js/org_structure.js`                   | Organization chart OWL component (d3-org-chart)                                         |
| `hcm/static/src/xml/org_structure.xml`                 | Organization chart template                                                             |
| `sales/models/models.py`                               | All sales models (customer, product, pricing, SO, invoice, payment, delivery, approval) |
| `sales/views/views.xml`                                | Form/tree views for all sales models                                                    |
| `sales/data/menu.xml`                                  | Sales menu structure                                                                    |
| `sales/data/sequence.xml`                              | Sales ID sequences                                                                      |
| `sales/data/mail_template_*.xml`                       | Email templates                                                                         |
| `disable_autosave/static/src/js/disable_autosave.js`   | Cancel button handler                                                                   |
| `disable_autosave/static/src/css/disable_autosave.css` | Cancel button styling                                                                   |
