# ERP KSI — Product Specification Document

> **Versi:** 1.0  
> **Terakhir diperbarui:** 2026-07-14  
> **Stack:** Odoo 17 (Python/OWL) + PostgreSQL  
> **Target:** Developer

---

## Daftar Isi

1. [Arsitektur Sistem](#1-arsitektur-sistem)
2. [Spesifikasi Modul](#2-spesifikasi-modul)
3. [Data Flow & State Machines](#3-data-flow--state-machines)
4. [Spesifikasi Data Model](#4-spesifikasi-data-model)
5. [Business Rules & Validation](#5-business-rules--validation)
6. [Security Specification](#6-security-specification)
7. [UI/UX Specification](#7-uiux-specification)
8. [Integration & Email](#8-integration--email)
9. [Referensi File](#9-referensi-file)

---

## 1. Arsitektur Sistem

### 1.1 Tech Stack

| Layer | Teknologi | Keterangan |
|-------|-----------|------------|
| **Platform** | Odoo 17 | Community/Enterprise |
| **Backend** | Python 3 | Odoo ORM |
| **Frontend** | OWL v2 | Component-based UI |
| **Database** | PostgreSQL | Via Odoo ORM |
| **CSS** | Bootstrap + Custom | Utility classes |
| **Icons** | Font Awesome | |
| **Org Chart** | d3.js v7 + d3-flextree v2.1.2 + d3-org-chart v2.6.0 | Via CDN |
| **Email** | Odoo `mail` module | Template-based |
| **Reporting** | QWeb PDF | Invoice reports |
| **Version Control** | Git | |

### 1.2 Module Dependency Graph

```
base
 └── disable_autosave                    # Patch auto-save behavior
      └── general                        # Core: master data, RBAC, NavigationMixin
           └── hcm                      # Human Capital Management
                └── sales               # Sales lifecycle (depends: mail)
```

### 1.3 Module Registry

| Module | Dependensi | Fungsi Utama |
|--------|------------|--------------|
| `disable_autosave` | `base` | Disable auto-save, custom Cancel button, user menu cleanup |
| `general` | `base`, `disable_autosave` | Master data, NavigationMixin, RBAC, home dashboard |
| `hcm` | `base`, `general`, `disable_autosave` | Position, Employee, org chart |
| `sales` | `base`, `general`, `hcm`, `disable_autosave`, `mail` | Quotation → SO → Invoice → Payment → Delivery |
| `user_management` | `base`, `general`, `hcm`, `disable_autosave` | UI for user & auth management |

### 1.4 Arsitektur Komponen

```
┌─────────────────────────────────────────────────────────────┐
│                    Odoo 17 Framework                        │
├─────────────────────────────────────────────────────────────┤
│  Frontend (OWL)                                             │
│  ├── FormController patch (disable_autosave.js)             │
│  ├── FormRenderer patch (disable_autosave.js)               │
│  └── OrgStructure component (org_structure.js)              │
├─────────────────────────────────────────────────────────────┤
│  Backend (Python/ORM)                                       │
│  ├── navigation.mixin (AbstractModel)                      │
│  ├── general module (RBAC, master data)                     │
│  ├── hcm module (employee, position, org chart)             │
│  ├── sales module (SO, invoice, payment, delivery)          │
│  └── mail module (Odoo core — email templates)              │
├─────────────────────────────────────────────────────────────┤
│  Database (PostgreSQL via ORM)                              │
│  ├── general_* (15 tables)                                  │
│  ├── hcm_* (6 tables)                                       │
│  └── sales_* (20+ tables)                                   │
└─────────────────────────────────────────────────────────────┘
```

### 1.5 Tidak Ada Custom API Routes

Kedua file `general/controllers/controllers.py` dan `sales/controllers/controllers.py` berisi placeholder yang dikomentari. Seluruh komunikasi client-server menggunakan mekanisme standar Odoo:

- **ORM RPC calls** — `useService("orm")` di OWL
- **Form actions** — `ir.actions.act_window`
- **Client actions** — `ir.actions.client` (misal: `hcm_org_structure`)
- **Email** — via `mail.compose.message` dengan template

---

## 2. Spesifikasi Modul

### 2.1 Module: `disable_autosave`

**Tujuan:** Disable fitur auto-save bawaan Odoo dan menangani perilaku tombol Cancel.

#### 2.1.1 Konfigurasi (`__manifest__.py`)

```python
# disable_autosave/__manifest__.py:10
'name': 'Disable Autosave by KSI'
'depends': ['base']
'assets': {
    'web.assets_backend': [
        'disable_autosave/static/src/js/disable_autosave.js',
        'disable_autosave/static/src/css/disable_autosave.css',
    ]
}
```

#### 2.1.2 JavaScript Behavior (`disable_autosave.js`)

**Global State** (line 10-12):
```javascript
let models = []                    // Model names yang disable auto-save
let auto_save_boolean_all = false  // Flag global "prevent all"
let auto_save_boolean = false      // Flag per-model
```

**Helper Functions:**

| Fungsi | Lokasi | Deskripsi |
|--------|--------|-----------|
| `loadPreventConfig(orm)` | Line 17 | Query `prevent.model.line` dan `prevent.model` via ORM |
| `shouldPrevent(model)` | Line 27 | Cek apakah auto-save harus diblokir untuk model tertentu |

**FormController Patch** (line 36-85):

| Method | Behavior |
|--------|----------|
| `setup()` | Load config via `loadPreventConfig()`, panggil `_disableBrowserAutoSave()` |
| `_disableBrowserAutoSave()` | Register event listener `beforeunload` (discard) dan `visibilitychange` (block) |
| `beforeLeave()` | Jika model match → `root.discard()` + return `true` (block navigasi) |
| `beforeUnload()` | Sama seperti `beforeLeave()` |

**FormRenderer Patch** (line 91-106):

| Method | Behavior |
|--------|----------|
| `onBlur(ev)` | Stop event propagation. Jika model match → `root.discard()` + return awal |

**Discard Button Handlers** (line 108-134):

| Tombol | CSS Class | Behavior |
|--------|-----------|----------|
| Discard New | `.discard-new` | Standard discard |
| Discard Edit | `.discard-edit` | Set `is_edit: false`, save, restore action |

**User Menu Cleanup** (line 136-173):

| Action | Item dihapus |
|--------|-------------|
| Custom menu | Tambahkan `"My Preferences"` (sequence 10, callback: `general.action_my_preferences`) |
| Cleanup | Hapus: `settings`, `documentation`, `support`, `odoo_account`, `shortcuts`, `debug` |

#### 2.1.3 Data Models

| Model | Tipe | Deskripsi |
|-------|------|-----------|
| `prevent.model` | Model | Flag global prevent auto-save |
| `prevent.model.line` | Model | Daftar model names yang di-disable |

---

### 2.2 Module: `general`

**Tujuan:** Core module — master data, NavigationMixin, RBAC, home dashboard.

#### 2.2.1 NavigationMixin (`general/models/models.py:138-348`)

AbstractModel yang diwarisi oleh semua master-data models.

**Fields:**

| Field | Tipe | Keterangan |
|-------|------|------------|
| `model_description` | Char (compute) | Deskripsi model |
| `user_can_read` | Boolean (compute) | Hak akses baca |
| `user_can_create` | Boolean (compute) | Hak akses buat |
| `user_can_update` | Boolean (compute) | Hak akses ubah |
| `user_can_delete` | Boolean (compute) | Hak akses hapus |

**Metode Utama:**

| Method | Lokasi | Deskripsi |
|--------|--------|-----------|
| `get_views()` | Line 149-221 | Auto-inject `readonly="not is_edit and id"` ke form fields; hide "New" button jika tidak punya `can_create` |
| `_compute_custom_permissions()` | Line 223-253 | Compute permission boolean dari `general.auth`. Admin selalu full access |
| `action_back()` | Line 259-269 | Kembali ke tree+form view |
| `action_back_kanban()` | Line 271-281 | Kembali ke kanban+form view |
| `action_edit()` | Line 283-300 | Set `is_edit=True`, buka form |
| `action_save()` | Line 302-322 | Set `is_edit=False`, buka form. Sync `name`/`login` ke `res.users` untuk custom_users |
| `action_delete()` | Line 324-338 | Hapus record. Cascade delete `res.users` untuk custom_users |
| `action_password()` | Line 340-348 | Buka wizard ganti password |

**Auto-Injection Logic (`get_views`):**

```
1. Jika user bukan admin:
   - Query general.auth untuk user + menu_code
   - Jika can_create=False → inject create="0" ke <list> dan <form>

2. Untuk form master-data (yang punya <field name="is_edit"/>):
   - Iterasi semua field di dalam <sheet>
   - Skip jika: sudah readonly, SYSTEM_FIELDS, invisible, di dalam <tree>,
     di dalam embedded <form>, computed tanpa inverse, model-level readonly
   - Inject: readonly="not is_edit and id"
```

**SYSTEM_FIELDS** (line 173-176):
```python
SYSTEM_FIELDS = {'id', 'is_edit', 'create_uid', 'create_date',
                 'write_uid', 'write_date', 'user_can_read',
                 'user_can_create', 'user_can_update', 'user_can_delete',
                 'model_description'}
```

#### 2.2.2 Master Data: Address Hierarchy

```
Country → State → City → District → Village
```

| Model | ID Field | Name Field | Parent Field | Sequence Code |
|-------|----------|------------|--------------|---------------|
| `general.country` | `country_id` | `country_name` | — | `general.country.sequence` |
| `general.state` | `state_id` | `state_name` | `country_ref` → country | `general.state.sequence` |
| `general.city` | `city_id` | `city_name` | `state_ref` → state | `general.city.sequence` |
| `general.district` | `district_id` | `district_name` | `city_ref` → city | `general.district.sequence` |
| `general.village` | `village_id` | `village_name` | `district_ref` → district | `general.village.sequence` |

**Domain Rules (Filter Dropdown):**

| Field | Domain | Kondisi |
|-------|--------|---------|
| `state` | `[('country_ref', '=', country)]` | Jika country kosong → tampilkan semua |
| `city` | `[('state_ref', '=', state)]` | Jika state kosong → tampilkan semua |
| `district` | `[('city_ref', '=', city)]` | Jika city kosong → tampilkan semua |
| `village` | `[('district_ref', '=', district)]` | Jika district kosong → tampilkan semua |

**Auto-Fill Cascade (Onchange Methods):**

| Trigger | Auto-fill Sequence | Lokasi |
|---------|-------------------|--------|
| Village dipilih | → District → City → State → Country | `hcm/models/models.py:240-255` |
| District dipilih | → City → State → Country | `hcm/models/models.py:257-269` |
| City dipilih | → State → Country | `hcm/models/models.py:271-280` |
| State dipilih | → Country | `hcm/models/models.py:282-288` |

#### 2.2.3 Master Data: Organization Hierarchy

```
Division → Department → Position
```

| Model | ID Field | Name Field | Parent Field | Sequence Code |
|-------|----------|------------|--------------|---------------|
| `general.division` | `division_id` | `division_name` | — | `general.division.sequence` |
| `general.department` | `department_id` | `department_name` | `division_id` → division | `general.department.sequence` |
| `general.position` | `position_id` | `position_name` | `department_id` → department | `general.position.sequence` |

**Auto-Fill Cascade:**

| Trigger | Auto-fill Sequence | Lokasi |
|---------|-------------------|--------|
| Position dipilih | → Department → Division | `hcm/models/models.py:294-303` |
| Department dipilih | → Division | `hcm/models/models.py:305-311` |

#### 2.2.4 Master Data: Organization

| Model | ID Field | Name Field | Sequence Code |
|-------|----------|------------|---------------|
| `general.company` | `company_id` | `company_name` | `general.company.sequence` |
| `general.location` | `location_id` | `location_name` | `general.location.sequence` |
| `general.level_grade` | `level_id` | `level_name` | `general.level_grade.sequence` |

#### 2.2.5 RBAC System

**Model: `general.custom_users`** (`general/models/models.py:748-864`)

| Field | Tipe | Keterangan |
|-------|------|------------|
| `custom_user_id` | Char | Auto-generated sequence |
| `name` | Char | Required |
| `login` | Char | Required |
| `password` | Char | Required |
| `position` | Many2one → `general.position` | |
| `user_id` | Many2one → `res.users` | Readonly, link ke Odoo user |
| `image_1920` | Image | Related to `user_id.image_1920` |
| `menu_ids` | One2many → `general.auth` | Domain: `is_parent=False` |

**Behavior:**
- `create()` (line 773): Auto-generate sequence, create `res.users` record, assign `base.group_user`
- `write()` (line 803): Sync `name`, `login`, `image` ke `res.users` + partner
- `unlink()` (line 859): Cascade delete `res.users`

**Model: `general.auth`** (`general/models/models.py:867-921`)

| Field | Tipe | Default |
|-------|------|---------|
| `custom_user_id` | Many2one → `general.custom_users` | ondelete=cascade |
| `user_id` | Many2one → `res.users` | related, readonly |
| `menu_id` | Many2one → `general.menu` | domain: `is_parent=False` |
| `is_parent` | Boolean | False |
| `can_create` | Boolean | False |
| `can_update` | Boolean | False |
| `can_delete` | Boolean | False |
| `can_submit` | Boolean | False |
| `can_send` | Boolean | False |
| `can_confirm` | Boolean | False |
| `can_invoicing` | Boolean | False |
| `can_receive` | Boolean | False |
| `can_billing` | Boolean | False |

**Behavior:**
- `create()` (line 888): Duplicate check → trigger `_refresh_related_user_menu_access()`
- `write()` (line 905): Trigger `_refresh_related_user_menu_access()`
- `unlink()` (line 911): Trigger `_refresh_custom_menu_access()`
- Context flag `skip_menu_refresh` untuk cegah infinite recursion

**Model: `general.menu`** (`general/models/models.py:649-657`)

| Field | Tipe | Keterangan |
|-------|------|------------|
| `menu_id` | Char | Unique identifier string |
| `menu_name` | Char | Display name |
| `parent_menu` | Char | Parent identifier string |
| `is_parent` | Boolean | Default False |

**Menu Visibility Engine** (`general/models/models.py:924-1053`):

```
ResUsers._refresh_custom_menu_access() (line 935-1018)
│
├── Admin → clear all restrictions, skip
│
└── Non-admin:
    ├── 1. Clear all existing restrict_user_ids from ir.ui.menu
    ├── 2. Clear hide_menu_ids on user record
    ├── 3. Delete auto-generated parent auth records (is_parent=True)
    ├── 4. Parent menu auto-propagation loop:
    │       Jika child menu authorized → auto-create parent auth
    │       Repeat sampai tidak ada parent baru
    └── 5. Semua menu TIDAK di authorized list → tambah ke restrict_user_ids
```

**Filter Visible Menus** (`general/models/models.py:1029-1053`):
```python
# ir.ui.menu._filter_visible_menus()
# Admin → semua menu visible
# Non-admin → filter out menus di restrict_user_ids
```

#### 2.2.6 Home Dashboard

**Model: `general.home`** (`general/models/models.py:660-745`)

| Field | Tipe | Keterangan |
|-------|------|------------|
| `show_hcm` | Boolean (compute) | Tampilkan card HCM |
| `show_sales` | Boolean (compute) | Tampilkan card Sales |
| `show_configuration` | Boolean (compute) | Tampilkan card Configuration |

**Logic:**
1. Admin → tampilkan semua card untuk installed modules
2. Non-admin → query `general.auth` untuk user, cek apakah ada auth menu di parent `hcm`, `sales`, atau `master_data`

#### 2.2.7 Password Wizards

| Model | Tipe | Lokasi | Deskripsi |
|-------|------|--------|-----------|
| `general.password` | TransientModel | Line 103-135 | Admin ganti password user lain. Validate match + min-length 6 |
| `general.password_preferences` | TransientModel | Line 5-62 | User ganti password sendiri. 2-step: verify old → set new |
| `general.preferences` | TransientModel | Line 65-100 | User profile: ubah name, photo, trigger password change |

---

### 2.3 Module: `hcm`

**Tujuan:** Human Capital Management — Position, Employee, Family, Education, Org Chart.

#### 2.3.1 Position (`hcm.position`) — `hcm/models/models.py:5-52`

| Field | Tipe | Keterangan |
|-------|------|------------|
| `position_id` | Char | Auto-generated, readonly |
| `name` | Char | Required |
| `department_id` | Many2one → `general.department` | Index |
| `parent_id` | Many2one → `hcm.position` | Self-referential, ondelete=set null |
| `child_ids` | One2many → `hcm.position` | Reverse of parent_id |
| `description` | Text | |
| `active` | Boolean | Default True (soft-delete) |
| `employee_count` | Integer | Computed from employee_ids |
| `employee_ids` | One2many → `hcm.employee` | |

**Name Get** (line 45-52): Menampilkan hierarki `"Parent / Position Name"`.

#### 2.3.2 Employee (`hcm.employee`) — `hcm/models/models.py:55-341`

**Tab 1: Data Karyawan** (line 62-103):

| Field | Tipe | Keterangan |
|-------|------|------------|
| `employee_id` | Char | Auto-generated, readonly |
| `name` | Char | Required |
| `nik` | Char | Required, unique (SQL constraint) |
| `phone` | Char | |
| `email` | Char | |
| `company_ref` | Many2one → `general.company` | |
| `location_ref` | Many2one → `general.location` | |
| `division_ref` | Many2one → `general.division` | |
| `department_id` | Many2one → `general.department` | Domain: by division_ref |
| `level_grade_ref` | Many2one → `general.level_grade` | |
| `position_id` | Many2one → `hcm.position` | Domain: by department_id + active=True |
| `manager_id` | Many2one → `hcm.employee` | **Computed** (store=True) |
| `join_date` | Date | |
| `status` | Selection | active/inactive/resigned/terminated, default=active |
| `photo` | Binary | attachment=True |
| `custom_user_id` | Many2one → `general.custom_users` | ondelete=set null |

**Tab 2: Data Pribadi** (line 105-171):

| Field | Tipe | Keterangan |
|-------|------|------------|
| `place_of_birth` | Char | |
| `date_of_birth` | Date | |
| `gender` | Selection | male/female |
| `religion` | Selection | islam/christian/catholic/hindu/buddha/konghucu/other |
| `blood_type` | Selection | a/b/ab/o |
| `first_name`, `last_name` | Char | |
| `nationality` | Char | |
| `kk_number`, `ktp_number`, `passport_number` | Char | Identitas |
| `passport_expiry_date`, `tax_date` | Date | |
| `height`, `weight` | Float | |
| `wear_glasses` | Boolean | |
| `age` | Integer | **Computed** dari `date_of_birth` |
| `npwp`, `bpjs_kesehatan`, `bpjs_ketenagakerjaan` | Char | Tax IDs |
| `country_id` → `village_id` | Many2one chain | Address hierarchy |
| `rt`, `rw`, `postal_code` | Char | |
| `bank_name`, `bank_account_number`, `bank_account_holder` | Char | Bank info |
| `marital_status` | Selection | single/married/divorced/widowed |
| `spouse_name`, `spouse_birth_date` | | |
| `children_count` | Integer | |
| `marriage_date` | Date | |

**Tab 3: Data Keluarga** (line 173-178):

| Model | Fields |
|-------|--------|
| `hcm.employee.family` | `employee_id`, `kk_number`, `nik`, `name`, `relation` (required: father/mother/spouse/child/sibling/other), `place_of_birth`, `date_of_birth`, `gender`, `last_education` (9 levels), `phone` |

**Tab 4: Pendidikan** (line 180-189):

| Model | Fields Utama |
|-------|-------------|
| `hcm.employee.education` | `level` (required: sd-s3), `institution` (required), `major`, `start_year`, `end_year`, `gpa`, `document` |
| `hcm.employee.certificate` | `name` (required), `issuer`, `date_issued`, `expiry_date`, `certificate_number`, `document` |
| `hcm.employee.training` | `name` (required), `organizer`, `date_start`, `date_end`, `duration_days` (computed+stored), `location`, `description`, `document` |

**Document Repository:**
- `attachment_ids`: Many2many → `ir.attachment`

**Computed Fields:**

| Field | Logic | Lokasi |
|-------|-------|--------|
| `manager_id` | Cari employee di parent position (position_id.parent_id) dengan status active | Line 208-220 |
| `age` | Hitung dari date_of_birth (kurangi 1 jika belum lewat ulang tahun tahun ini) | Line 222-234 |

**SQL Constraint:**
```python
# hcm/models/models.py:203-206
_sql_constraints = [
    ('nik_unique', 'unique(nik)',
     'NIK must be unique! An employee with this NIK already exists.')
]
```

#### 2.3.3 Organization Chart

| Aspek | Detail |
|-------|--------|
| **Teknologi** | OWL Component (`OrgStructure`) + d3-org-chart v2.6.0 |
| **Entry Point** | Client action `hcm_org_structure` |
| **Lokasi** | `hcm/static/src/js/org_structure.js:11-215` |
| **Template** | `hcm/static/src/xml/org_structure.xml` |

**Data Loading** (line 60-112):
1. Parallel fetch `hcm.position` (active) dan `hcm.employee` (active) via ORM
2. Build employee-by-position map
3. Construct `flatData` array: `{id, parentId, name, department, employee_count, employees}`
4. Handle edge cases:
   - 0 roots → make first node root
   - Multiple roots → create virtual root node

**Rendering** (line 121-204):
- `nodeWidth=240`, `nodeHeight=130`
- `childrenMargin=60`, `compactMarginBetween=30`, `compactMarginPair=80`, `siblingsMargin=20`
- Node content: gradient header, department, employee count, up to 4 employee names
- Interactions: scroll zoom, drag pan, click expand/collapse

**XSS Prevention** (line 205):
```javascript
_escapeHtml(str) {
    const el = document.createElement('span');
    el.textContent = str;
    return el.innerHTML;
}
```

---

### 2.4 Module: `sales`

**Tujuan:** Full sales lifecycle — Customer, Product, Pricing, SO, Invoice, Payment, Delivery.

#### 2.4.1 Customer Master Data

**Model: `sales.customer`** (`sales/models/models.py:312-543`)

| Field | Tipe | Keterangan |
|-------|------|------------|
| `customer_id` | Char | Auto-generated, readonly |
| `customer_name` | Char | |
| `address` | Text | |
| `country` → `district` | Many2one chain | Address hierarchy (4 level, tanpa village) |
| `postal_code` | Char | |
| `sales_name` | Many2one → `general.custom_users` | Domain: Sales menus |
| `npwp` | Char | |
| `cust_category` | Many2one → `sales.cust_category` | Required |
| `cust_type` | Many2one → `sales.cust_type` | |
| `cust_area` | Many2one → `sales.cust_area` | |
| `price_condition_ids` | Many2many → `sales.price_condition` | Through: `customer_price_condition_rel` |
| `payment_terms` | Many2one → `sales.payment_terms` | Domain: Account Type = Customer |
| `contact_name`, `telephone`, `email`, `website` | Char | Contact info |
| `ship_to_ids` | One2many → `sales.ship_to` | |
| `partner_id` | Many2one → `res.partner` | Auto-created |
| `image_1920` | Binary | |
| `avatar_128` | Binary | Related |

**Behavior:**
- `create()` (line 400): Generate sequence, **create `res.partner`** (name, email, phone, street, city, country, state, user_id, vat, image)
- `write()` (line 444): Sync ke `res.partner`. Jika `cust_category` berubah → trigger `_resync_price_conditions()`
- `unlink()` (line 507): Cascade delete `res.partner`

**Price Condition Sync** (`_resync_price_conditions`, line 521):
1. Hapus semua M2M link via raw SQL
2. Query `sales.price_condition` yang applicable (valid dates + customer scope match)
3. Tambahkan condition ke M2M link

**Model: `sales.ship_to`** (`sales/models/models.py:559-628`)

| Field | Tipe | Keterangan |
|-------|------|------------|
| `ship_id` | Char | Auto-generated |
| `ship_name` | Char | |
| `customer_id` | Many2one → `sales.customer` | ondelete=cascade |
| `address` | Text | |
| `country` → `district` | Many2one chain | Address hierarchy |

**Supporting Models:**

| Model | Fields |
|-------|--------|
| `sales.cust_category` | `category_id` (auto-gen), `category_name`. **Blocked deletion** jika ada customer reference |
| `sales.cust_type` | `type_id` (auto-gen), `type_name` |
| `sales.cust_area` | `area_id` (auto-gen), `area_name` |

#### 2.4.2 Product Master Data

**Model: `sales.products`** (`sales/models/models.py:686-767`)

| Field | Tipe | Keterangan |
|-------|------|------------|
| `product_id` | Char | Auto-generated |
| `product_name` | Char | |
| `sales_ok` | Boolean | Default True |
| `purchase_ok` | Boolean | Default True |
| `barcode` | Char | |
| `product_type` | Many2one → `sales.product_type` | |
| `product_category` | Many2one → `sales.product_category` | Required |
| `product_unit` | Many2one → `sales.product_unit` | |
| `base_price` | Float | digits=(16,0) |
| `currency_id` | Many2one → `res.currency` | Default IDR |
| `price` | Float | Computed: base_price + tax |
| `tax_string` | Char | Computed: `"(= X Incl. Taxes)"` |
| `customer_tax` | Many2one → `sales.taxes` | Default: first default_tax |
| `stock` | Integer | Default 0 |
| `sales_order_line_ids` | One2many → `sales.sales_order_line` | |
| `qty_reserved_sale` | Integer | **Computed+stored**: stock booked on open SOs |
| `image` | Binary | |

**Constant** (line 681):
```python
RESERVED_SO_STATES = ('draft', 'sale_draft', 'wait_approval', 'approved', 'sent', 'sale')
```

**Computed Fields:**

| Field | Logic | Lokasi |
|-------|-------|--------|
| `tax_string` | `"(= {price} Incl. Taxes)"` | Line 739 |
| `qty_reserved_sale` | Sum qty dari SO lines di RESERVED_SO_STATES | Line 751 |

**Supporting Models:**

| Model | Fields |
|-------|--------|
| `sales.product_type` | `name` |
| `sales.product_category` | `category_name`. **Blocked deletion** jika ada product reference |
| `sales.product_unit` | `uom`, `qty`, `base_uom`, `base_qty` |
| `sales.taxes` | `name`, `tax_percentage`, `default_tax` (singleton — hanya satu yang True) |

#### 2.4.3 Price Conditions

**Model: `sales.price_condition`** (`sales/models/models.py:769-888`)

| Field | Tipe | Keterangan |
|-------|------|------------|
| `price_name` | Char | |
| `date_start`, `date_end` | Datetime | Validity period |
| `min_quantity` | Integer | Default 1 |
| `compute_price` | Selection | fixed/discount |
| `fixed_price` | Float | digits=(16,0) |
| `percent_price` | Float | Discount % |
| `price` | Char | Computed: display |
| `applied_on` | Selection | all/category/product (Product scope) |
| `product_category_ids` | Many2many → `sales.product_category` | |
| `product_ids` | One2many → `sales.price_condition_product` | |
| `product_priority` | Integer | Computed: all=3, category=2, product=1 |
| `customer_applied_on` | Selection | all/category/customer (Customer scope) |
| `customer_category_ids` | Many2many → `sales.cust_category` | |
| `customer_ids` | One2many → `sales.price_condition_customer` | |
| `customer_priority` | Integer | Computed: all=3, category=2, customer=1 |

**Ordering:**
```python
_order = 'customer_priority asc, product_priority asc, id desc'
```

**Sync Logic** (`_sync_to_customers`, line 830):
1. Hapus semua M2M link via raw SQL
2. Cari target customers berdasarkan `customer_applied_on`:
   - `all` → semua customers
   - `category` → customers di category yang match
   - `customer` → customers spesifik
3. Tambahkan condition ke matching customers via `(4, id)` command

#### 2.4.4 Payment Terms

**Model: `sales.payment_terms`** (`sales/models/models.py:919-1002`)

| Field | Tipe | Keterangan |
|-------|------|------------|
| `payment_terms_id` | Char | Auto-generated |
| `sales_text` | Char | |
| `early_discount` | Boolean | |
| `discount_percentage` | Float | digits=(3,0) |
| `discount_days` | Integer | |
| `account_type` | Many2many → `sales.account_type` | Required |
| `baseline_date` | Selection | doc/post/entry, default=doc |
| `example_amount` | Float | Default 10000000 |
| `example_date` | Date | Default today |
| `note` | Html | |
| `example_preview_discount` | Html | Computed |
| `example_preview` | Html | Computed |
| `payment_terms_ids` | One2many → `sales.payment_terms_detail` | |

**Detail Lines** (`sales.payment_terms_detail`, line 1004-1024):

| Field | Tipe |
|-------|------|
| `payment_terms_id` | Many2one → `sales.payment_terms` |
| `percentage` | Float |
| `no_of_days` | Integer |
| `explanation` | Char (computed): "After document/posting/entry date" |

#### 2.4.5 Terms & Conditions

**Model: `sales.terms_and_conditions`** (`sales/models/models.py:2458-2466`)

| Field | Tipe |
|-------|------|
| `content` | Text |
| `is_edit` | Boolean |

Default content di-load ke `note` field di sales order baru via `default_get()`.

---

## 3. Data Flow & State Machines

### 3.1 Sales Order State Machine

#### 3.1.1 Quotation Flow (`is_quotation=True`)

```
                    ┌──────────────────────────────────────────────────────┐
                    │                    QUOTATION FLOW                    │
                    └──────────────────────────────────────────────────────┘

    ┌─────────┐    submit     ┌──────────────┐    approve    ┌──────────┐
    │  draft   │────────────→ │ wait_approval │─────────────→ │ approved │
    └─────────┘              └──────────────┘               └──────────┘
         │                         │    │                         │
         │                         │    │ reject                  │ send
         │                         │    ▼                         ▼
         │                         │  ┌────────┐            ┌──────────┐
         │                         │  │ cancel │            │  sent    │
         │                         │  └────────┘            └──────────┘
         │                         │                            │
         │                         │ return                     │ confirm
         │                         ▼                            ▼
         │                    ┌────────────┐               ┌─────────┐
         └───cancel────────→  │   (reset)  │               │  sale   │
                              └────────────┘               └─────────┘
```

#### 3.1.2 Sales Order Flow (`is_quotation=False`)

```
                    ┌──────────────────────────────────────────────────────┐
                    │               SALES ORDER FLOW                      │
                    └──────────────────────────────────────────────────────┘

    ┌────────────┐    submit     ┌──────────────┐    approve    ┌──────────┐
    │ sale_draft │────────────→  │ wait_approval │─────────────→ │ approved │
    └────────────┘              └──────────────┘               └──────────┘
         │                          │    │                          │
         │                          │    │ reject                   │ confirm
         │                          │    ▼                          ▼
         │                          │  ┌────────┐              ┌─────────┐
         └─────cancel────────────→  │  │ cancel │              │  sale   │
                                    │  └────────┘              └─────────┘
                                    │                              │
                                    │ return                       │ create invoice
                                    ▼                              ▼
                               ┌────────────┐               ┌──────────┐
                               │   (reset)  │               │ invoiced │
                               └────────────┘               └──────────┘
```

### 3.2 Approval Workflow

**Multi-level Sequential Approval** (`sales/models/models.py:1608-2007`)

```
┌─────────────────────────────────────────────────────────────┐
│                   APPROVAL WORKFLOW                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. SO Line ditambah/diubah                                  │
│     └── _check_approval_requirement() dipanggil              │
│                                                              │
│  2. Cek apakah approval diperlukan:                          │
│     ├── Total amount > matrix.min_amount?                    │
│     └── Line discount > base_discount?                       │
│                                                              │
│  3. Jika Ya → buat approval_log entries dari matrix          │
│     (sorted by sequence)                                     │
│                                                              │
│  4. Submit → state = wait_approval                           │
│     └── Kirim email ke first pending approver                 │
│                                                              │
│  5. Approvers act in sequence:                               │
│     ├── APPROVE → next approver atau fully approved          │
│     ├── REVISE → kirim pesan, reset approval chain           │
│     ├── RETURN → kirim balik, approver di bawah re-approve   │
│     └── REJECT → cancel SO                                   │
│                                                              │
│  6. Email notification ke pending approver berikutnya         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Approval Matrix** (`sales.sales_approval_matrix`, line 2468-2494):

| Field | Tipe | Keterangan |
|-------|------|------------|
| `name` | Many2one → `general.custom_users` | Approver |
| `sequence` | Integer | Urutan approval |
| `position` | Many2one | Related |
| `receive_return` | Boolean | Jika True, approver ini menerima return |
| `min_amount` | Float | Threshold jumlah minimum |
| `approve` | Boolean | Bisa approve |
| `revise` | Boolean | Bisa revise |
| `returned` | Boolean | Status returned |
| `reject` | Boolean | Bisa reject |
| `printed` | Boolean | |
| `notify` | Boolean | |
| `approved_as` | Selection | proposer/checker/approver/validator/finalizer |

**Approval Log** (`sales.sales_approval_log`, line 2497-2529):

| Field | Tipe | Keterangan |
|-------|------|------------|
| `sales_order_id` | Many2one → `sales.sales_order` | ondelete=cascade |
| `approver` | Char | Nama approver |
| `email` | Char | Email approver |
| `position` | Char | |
| `action_date` | Datetime | Kapan action diambil |
| `state` | Selection | pending/approved/revised/returned/rejected |
| `sequence` | Integer | Urutan |
| `min_amount` | Float | |
| `note` | Text | |
| `approval_reason` | Text | Alasan approve/reject |

### 3.3 Invoice State Machine

```
    ┌─────────┐     post      ┌──────────┐
    │  draft   │─────────────→│  posted  │
    └─────────┘               └──────────┘
         │                         │
         │ cancel                  │ create credit note
         ▼                         ▼
    ┌──────────┐            ┌──────────────┐
    │  cancel  │            │ credit_note  │
    └──────────┘            └──────────────┘
         │
         │ set_to_draft
         ▼
    ┌─────────┐
    │  draft   │
    └─────────┘
```

**Invoice Types:**
- Regular Invoice — full invoice dengan semua SO lines
- Down Payment (Percentage) — invoice untuk % dari total
- Down Payment (Fixed) — invoice untuk jumlah tetap

**Document Types:**
- Invoice
- Credit Note (reverse dari posted invoice)

### 3.4 Payment State Machine

```
    ┌─────────┐     post      ┌──────────┐
    │  draft   │─────────────→│  posted  │
    └─────────┘               └──────────┘
         │                         │
         │ cancel                  │ (no further state)
         ▼                         │
    ┌──────────┐                    │
    │  cancel  │                    │
    └──────────┘                    │
         │                          │
         │ reset_to_draft           │
         ▼                          │
    ┌─────────┐                     │
    │  draft   │ ←──────────────────┘
    └─────────┘

    Payment Methods: manual, bank_transfer, check, cash
```

### 3.5 Delivery State Machine

```
    ┌─────────┐     done      ┌──────────┐
    │  draft   │─────────────→│   done   │
    └─────────┘               └──────────┘
         │
         │ cancel
         ▼
    ┌──────────┐
    │  cancel  │
    └──────────┘
```

### 3.6 Credit Note Flow

```
    Posted Invoice
         │
         │ action_create_credit_note
         ▼
    ┌──────────────┐
    │ credit_note  │ (copy all lines, reverse sign)
    │ state=draft  │
    └──────────────┘
         │
         │ action_post
         ▼
    ┌──────────────┐
    │ credit_note  │ (posted, journal items generated)
    │ state=posted │
    └──────────────┘
```

### 3.7 Invoice Creation Flow

```
    Sales Order (state=sale)
         │
         │ action_create_invoice_simple
         ▼
    ┌────────────────────────────┐
    │ Create Invoice Wizard      │
    │ - regular                  │
    │ - down_payment_percentage  │
    │ - down_payment_fixed       │
    └────────────────────────────┘
         │
         │ create_custom_invoice
         ▼
    ┌──────────────────────┐
    │ sales.invoice         │
    │ state=draft           │
    │ journal items rebuilt │
    └──────────────────────┘
         │
         │ action_post
         ▼
    ┌──────────────────────┐
    │ sales.invoice         │
    │ state=posted          │
    └──────────────────────┘
```

---

## 4. Spesifikasi Data Model

### 4.1 general Module

| Model | Table | Tipe | Key Fields |
|-------|-------|------|------------|
| `navigation.mixin` | — | AbstractModel | `model_description`, `user_can_*` |
| `general.country` | `general_country` | Model | `country_id`, `country_name` |
| `general.state` | `general_state` | Model | `state_id`, `state_name`, `country_ref` |
| `general.city` | `general_city` | Model | `city_id`, `city_name`, `state_ref` |
| `general.district` | `general_district` | Model | `district_id`, `district_name`, `city_ref` |
| `general.village` | `general_village` | Model | `village_id`, `village_name`, `district_ref` |
| `general.company` | `general_company` | Model | `company_id`, `company_name` |
| `general.location` | `general_location` | Model | `location_id`, `location_name` |
| `general.division` | `general_division` | Model | `division_id`, `division_name`, `department_ids` |
| `general.department` | `general_department` | Model | `department_id`, `department_name`, `division_id` |
| `general.position` | `general_position` | Model | `position_id`, `position_name`, `department_id` |
| `general.level_grade` | `general_level_grade` | Model | `level_id`, `level_name` |
| `general.menu` | `general_menu` | Model | `menu_id`, `menu_name`, `parent_menu`, `is_parent` |
| `general.home` | `general_home` | Model | `show_hcm`, `show_sales`, `show_configuration` |
| `general.custom_users` | `general_custom_users` | Model | `custom_user_id`, `name`, `login`, `password`, `user_id`, `menu_ids` |
| `general.auth` | `general_auth` | Model | `custom_user_id`, `menu_id`, `can_create/update/delete/submit/send/confirm/invoicing/receive/billing` |
| `general.password` | — | TransientModel | `user_id`, `new_password`, `confirm_password` |
| `general.password_preferences` | — | TransientModel | `user_id`, `old_password`, `new_password`, `confirm_password` |
| `general.preferences` | — | TransientModel | `user_id`, `name`, `image_1920`, `login` |
| `res.users` (inherited) | `res_users` | Inherited | `hide_menu_ids` |
| `ir.ui.menu` (inherited) | `ir_ui_menu` | Inherited | `restrict_user_ids` |

### 4.2 hcm Module

| Model | Table | Key Fields |
|-------|-------|------------|
| `hcm.position` | `hcm_position` | `position_id`, `name`, `department_id`, `parent_id`, `child_ids`, `employee_count` |
| `hcm.employee` | `hcm_employee` | `employee_id`, `name`, `nik`, `position_id`, `manager_id` (computed), `status`, `photo`, address hierarchy, bank info, marriage info |
| `hcm.employee.family` | `hcm_employee_family` | `employee_id`, `kk_number`, `nik`, `name`, `relation`, `gender`, `last_education` |
| `hcm.employee.education` | `hcm_employee_education` | `employee_id`, `level`, `institution`, `major`, `gpa`, `document` |
| `hcm.employee.certificate` | `hcm_employee_certificate` | `employee_id`, `name`, `issuer`, `date_issued`, `expiry_date`, `document` |
| `hcm.employee.training` | `hcm_employee_training` | `employee_id`, `name`, `organizer`, `date_start`, `date_end`, `duration_days` (stored) |

### 4.3 sales Module

| Model | Table | Key Fields |
|-------|-------|------------|
| `sales.cust_category` | `sales_cust_category` | `category_id`, `category_name` |
| `sales.cust_type` | `sales_cust_type` | `type_id`, `type_name` |
| `sales.cust_area` | `sales_cust_area` | `area_id`, `area_name` |
| `sales.customer` | `sales_customer` | `customer_id`, `customer_name`, address hierarchy, `cust_category`, `cust_type`, `cust_area`, `price_condition_ids`, `payment_terms`, `partner_id` |
| `sales.ship_to` | `sales_ship_to` | `ship_id`, `ship_name`, `customer_id`, address hierarchy |
| `sales.product_type` | `sales_product_type` | `name` |
| `sales.product_category` | `sales_product_category` | `category_name` |
| `sales.product_unit` | `sales_product_unit` | `uom`, `qty`, `base_uom`, `base_qty` |
| `sales.products` | `sales_products` | `product_id`, `product_name`, `product_category`, `base_price`, `price`, `customer_tax`, `stock`, `qty_reserved_sale` |
| `sales.taxes` | `sales_taxes` | `name`, `tax_percentage`, `default_tax` |
| `sales.price_condition` | `sales_price_condition` | `price_name`, `date_start/end`, `compute_price`, `fixed_price`, `percent_price`, `applied_on`, `customer_applied_on` |
| `sales.price_condition_product` | `sales_price_condition_product` | `price_id`, `product_id` |
| `sales.price_condition_customer` | `sales_price_condition_customer` | `price_id`, `customer_id` |
| `sales.account_type` | `sales_account_type` | `name` |
| `sales.payment_terms` | `sales_payment_terms` | `payment_terms_id`, `sales_text`, `early_discount`, `account_type`, `baseline_date` |
| `sales.payment_terms_detail` | `sales_payment_terms_detail` | `payment_terms_id`, `percentage`, `no_of_days` |
| `sales.terms_and_conditions` | `sales_terms_and_conditions` | `content` |
| `sales.sales_approval_matrix` | `sales_sales_approval_matrix` | `name`, `sequence`, `min_amount`, `approve/revise/reject/receive_return` |
| `sales.sales_order` | `sales_sales_order` | `sales_code`, `customer_id`, `state`, `order_line_ids`, `total_amount`, `approval_log_ids`, `invoice_status` |
| `sales.sales_order_line` | `sales_sales_order_line` | `sales_order_id`, `product_id`, `quantity`, `unit_price`, `discount`, `base_discount`, `sub_total`, `info` |
| `sales.sales_approval_log` | `sales_sales_approval_log` | `sales_order_id`, `approver`, `state`, `sequence`, `note` |
| `sales.invoice` | `sales_invoice` | `invoice_number`, `sales_order_id`, `customer_id`, `state`, `invoice_type`, `document_type`, `amount_total`, `payment_state` |
| `sales.invoice.line` | `sales_invoice_line` | `invoice_id`, `product_id`, `description`, `quantity`, `unit_price`, `discount`, `tax_id`, `sub_total` |
| `sales.invoice.journal.item` | `sales_invoice_journal_item` | `invoice_id`, `line_type`, `account_code`, `debit`, `credit` |
| `sales.payment` | `sales_payment` | `payment_number`, `invoice_id`, `customer_id`, `payment_date`, `payment_method`, `amount`, `state` |
| `sales.payment.journal.item` | `sales_payment_journal_item` | `payment_id`, `line_type`, `account_code`, `debit`, `credit` |
| `sales.delivery` | `sales_delivery` | `delivery_number`, `sales_order_id`, `customer_id`, `delivery_date`, `state`, `line_ids` |
| `sales.delivery.line` | `sales_delivery_line` | `delivery_id`, `sales_order_line_id`, `product_id`, `ordered_qty`, `quantity` |

### 4.4 Relationship Map

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
├── hcm.position → department, parent (self-ref)
├── hcm.employee → position, department, division, location, company, level_grade, custom_users
│   ├── hcm.employee.family → employee (cascade)
│   ├── hcm.employee.education → employee (cascade)
│   ├── hcm.employee.certificate → employee (cascade)
│   └── hcm.employee.training → employee (cascade)

sales
├── sales.customer → category, type, area, salesperson, payment_terms, partner
│   └── sales.ship_to → customer (cascade)
├── sales.products → type, category, unit, customer_tax
├── sales.price_condition → product_category (m2m), product (o2m), cust_category (m2m), customer (o2m)
├── sales.payment_terms → account_type (m2m)
│   └── sales.payment_terms_detail → payment_terms
├── sales.sales_order → customer, payment_terms, salesperson
│   ├── sales.sales_order_line → sales_order (cascade), product, taxes
│   └── sales.sales_approval_log → sales_order (cascade)
├── sales.invoice → sales_order (restrict), customer (restrict), payment_terms
│   ├── sales.invoice.line → invoice (cascade), product, tax
│   ├── sales.invoice.journal.item → invoice (cascade)
│   └── sales.invoice → source_invoice_id (credit note)
├── sales.payment → invoice (restrict), customer (restrict)
│   └── sales.payment.journal.item → payment (cascade)
├── sales.delivery → sales_order (restrict), customer (restrict)
│   └── sales.delivery.line → delivery (cascade), sales_order_line, product
```

---

## 5. Business Rules & Validation

### 5.1 Price Condition Matching Algorithm

**Lokasi:** `sales/models/models.py:2283-2349` (method `_onchange_product_id_price_condition`)

```
INPUT: product_id, customer_id, quantity
OUTPUT: unit_price, discount, base_discount

ALGORITHM:
1. Build domain filter:
   ├── date_start <= today <= date_end
   ├── customer_applied_on == 'all'
   │   OR customer_applied_on == 'category' AND customer.cust_category IN customer_category_ids
   │   OR customer_applied_on == 'customer' AND customer IN customer_ids
   └── min_quantity <= quantity

2. Search sales.price_condition
   ORDER BY customer_priority ASC, product_priority ASC, id DESC

3. For each condition (sorted):
   ├── Product scope check:
   │   ├── applied_on == 'all' → match
   │   ├── applied_on == 'category' → product.product_category IN product_category_ids
   │   └── applied_on == 'product' → product IN product_ids
   │
   └── On first product match:
       ├── compute_price == 'fixed' → set unit_price = fixed_price, discount = 0
       └── compute_price == 'discount' → set discount = percent_price, base_discount = percent_price
       └── BREAK (most specific wins)
```

**Priority Matrix:**

| Customer Scope | Product Scope | customer_priority | product_priority |
|----------------|---------------|-------------------|------------------|
| All | All | 3 | 3 |
| All | Category | 3 | 2 |
| All | Specific | 3 | 1 |
| Category | All | 2 | 3 |
| Category | Category | 2 | 2 |
| Category | Specific | 2 | 1 |
| Specific | All | 1 | 3 |
| Specific | Category | 1 | 2 |
| Specific | Specific | 1 | 1 |

### 5.2 Stock Indent Detection

**Lokasi:** `sales/models/models.py:1586-1606, 2259-2280`

```
VARIABEL:
- product.stock           → stok fisik
- product.qty_reserved_sale → stok yang sudah dibooking di open SOs
- FREE_STOCK = max(0, product.stock - product.qty_reserved_sale)
- DEMAND = jumlah qty untuk product yang sama di SO yang sedang dibuka
- INDETS = jumlah Indent products di SO yang sedang dibuka

ALGO:
1. Untuk setiap SO line:
   ├── Hitung DEMAND (total qty product ini di semua line di SO yang sama)
   ├── Hitung INDETS (jumlah line lain yang sudah Indent untuk product ini)
   ├── Sisa stock untuk line ini = FREE_STOCK - INDETS
   │
   └── Jika DEMAND > FREE_STOCK → info = "Indent"
       Jika DEMAND <= FREE_STOCK → info = ""

2. Auto-refresh saat:
   ├── Product diubah
   ├── Quantity diubah
   └── Line ditambah/dihapus
```

**RESERVED_SO_STATES** (line 681):
```python
('draft', 'sale_draft', 'wait_approval', 'approved', 'sent', 'sale')
```

### 5.3 Journal Item Auto-Generation

**Invoice Journal Items** (`sales/models/models.py:2755-2872`):

```
TYPE: RECEIVABLE (account 110000)
├── Jika ada payment terms → split by installments
│   ├── Setiap installment: amount * percentage / 100
│   └── due_date = baseline_date + no_of_days
├── Jika tidak ada → satu line penuh
│
TYPE: REVENUE (account 400000)
├── Satu line per invoice line
├── amount = sub_total
│
TYPE: TAX (account 210000)
├── Digroup by tax_id
├── amount = sum(tax_amount) per tax
```

**Credit Note:**
- Menggunakan sign multiplier = -1
- Semua lines di-copy dengan tanda negatif

**Payment Journal Items** (`sales/models/models.py:3405-3430`):

```
LINE 1: Debit Cash/Bank (account 100000)
├── amount = payment.amount
│
LINE 2: Credit Account Receivable (account 110000)
├── amount = payment.amount
```

### 5.4 Customer-Partner Sync

**Lokasi:** `sales/models/models.py:400-519`

```
CREATE:
├── Generate sequence ID
├── Create res.partner:
│   ├── name = customer_name
│   ├── email = email
│   ├── phone = telephone
│   ├── street = address
│   ├── city = city.name (if mapped to res.city)
│   ├── country_id = country.id (mapped to res.country)
│   ├── state_id = state.id (mapped to res.country.state)
│   ├── vat = npwp
│   ├── image_1920 = image
│   └── user_id = sales_name.user_id
├── Store partner_id

WRITE:
├── Sync changed fields ke res.partner
├── Jika cust_category berubah → _resync_price_conditions()

UNLINK:
└── Cascade delete res.partner
```

### 5.5 Tax Default Singleton Rule

**Lokasi:** `sales/models/models.py:2442-2456`

```python
# Hanya satu tax yang boleh memiliki default_tax=True
# Jika ada tax baru yang set default_tax=True:
#   → Reset semua lain ke False
```

### 5.6 Blocked Deletion Rules

| Model | Kondisi | Error Message |
|-------|---------|---------------|
| `sales.cust_category` | Ada `sales.customer` yang reference | "Cannot delete category: it is used by customers" |
| `sales.product_category` | Ada `sales.products` yang reference | "Cannot delete category: it is used by products" |
| `sales.delivery` | State = done | "Cannot delete completed delivery" |

### 5.7 Approval Trigger Rules

**Lokasi:** `sales/models/models.py:1608-1708`

```
APPROVAL DIPERLUKAN JIKA:
1. Total amount SO > min_amount dari approval matrix yang applicable
   ATAU
2. Salah satu line discount > base_discount dari line tersebut

APPROVAL TIDAK DIPERLUKAN JIKA:
- Semua line discount <= base_discount
- Total amount <= semua min_amount thresholds
```

### 5.8 Payment Validation Rules

| Rule | Keterangan |
|------|------------|
| Amount <= amount_due | Pembayaran tidak boleh melebihi sisa tagihan |
| Amount > 0 | Pembayaran harus positif |
| Invoice state = posted | Hanya invoice yang sudah posted yang bisa dibayar |

### 5.9 Invoice Creation Rules

| Rule | Keterangan |
|------|------------|
| SO state = sale | Hanya SO yang sudah confirmed |
| Ada SO lines | Minimal ada satu line |
| Invoice state = draft | Tidak boleh buat invoice baru jika ada draft invoice |
| Down payment setelah regular | Tidak boleh buat down payment jika sudah ada regular invoice |

---

## 6. Security Specification

### 6.1 Authentication

- Standard Odoo `res.users` authentication
- Custom users (`general.custom_users`) linked 1:1 dengan `res.users`
- On login → `_update_last_login()` → trigger `_refresh_custom_menu_access()`

### 6.2 Authorization (RBAC)

#### Admin (`base.group_system`)

- Full unrestricted access ke semua menus dan actions
- Bypass semua permission checks

#### Non-Admin Users

**Menu Visibility:**
- Dikontrol oleh `ir.ui.menu.restrict_user_ids`
- Hanya menu yang ada di `general.auth` yang visible

**CRUD Permissions per Menu:**

| Permission | Field | Deskripsi |
|------------|-------|-----------|
| Create | `can_create` | Bisa membuat record baru |
| Update | `can_update` | Bisa mengubah record |
| Delete | `can_delete` | Bisa menghapus record |

**Workflow Permissions per Menu:**

| Permission | Field | Deskripsi |
|------------|-------|-----------|
| Submit | `can_submit` | Bisa submit untuk approval |
| Send | `can_send` | Bisa kirim email/quotation |
| Confirm | `can_confirm` | Bisa konfirmasi SO |
| Invoicing | `can_invoicing` | Bisa buat invoice |
| Receive | `can_receive` | Bisa terima pembayaran |
| Billing | `can_billing` | Bisa proses billing |

#### Enforcement Points

| Lokasi | Mekanisme |
|--------|-----------|
| `NavigationMixin.get_views()` | Sembunyikan tombol "New" jika `can_create=False` |
| `NavigationMixin._compute_custom_permissions()` | Set `user_can_*` fields |
| `sales.sales_order._check_cancel_order_access()` | Cek `can_delete` untuk cancel SO |
| `sales.sales_order._check_invoicing_access()` | Cek `can_invoicing` |
| `sales.invoice._check_invoicing_access()` | Cek `can_invoicing` |
| Individual action methods | Cek permission sebelum eksekusi |

### 6.3 Access Control Flow

```
User Login
    │
    ├── res.users authenticate
    ├── _update_last_login() called
    │   └── _refresh_custom_menu_access()
    │       ├── Clear all restrict_user_ids
    │       ├── Clear hide_menu_ids
    │       ├── Delete auto-generated parent auth
    │       ├── Parent menu propagation loop
    │       └── Add unauthorized menus to restrict_user_ids
    │
    └── Menu rendered
        └── _filter_visible_menus()
            └── Filter out menus di restrict_user_ids
```

### 6.4 CSV Access Rights

Setiap module mendefinisikan `security/ir.model.access.csv` untuk model-level CRUD access control.

---

## 7. UI/UX Specification

### 7.1 NavigationMixin Form Pattern

```
┌─────────────────────────────────────────────────────┐
│  [Back]  [Edit]  [Save]  [Cancel]  [Delete]  [🔑]  │  ← Header buttons
├─────────────────────────────────────────────────────┤
│                                                     │
│  <field name="is_edit" invisible="1"/>              │  ← Hidden field
│                                                     │
│  ┌─ <sheet> ─────────────────────────────────────┐  │
│  │                                                │  │
│  │  Semua fields: readonly="not is_edit and id"   │  │  ← Auto-injected
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**State Behavior:**

| State | `is_edit` | `id` | `readonly` expression | Field State |
|-------|-----------|------|----------------------|-------------|
| New record | False | False | `not False and False` = False | **Editable** |
| View mode | False | True | `not False and True` = True | **Readonly** |
| Edit mode | True | True | `not True and True` = False | **Editable** |

### 7.2 Kanban View Standard

**Struktur HTML:**

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

**CSS Standard:**

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

**Aturan:**

| Aturan | Keterangan |
|--------|------------|
| Full Height | Foto mengisi tinggi penuh card |
| Left Aligned | Foto selalu di kiri |
| Object Fit: Cover | Tanpa distorsi |
| Fixed Width | Lebar foto tetap 100px |
| Min Height | Minimum 100px |
| No Border Radius | Tanpa rounded corners |
| Flex Layout | Foto kiri (fixed), details kanan (flex:1) |

**Penerapan:** `hcm/static/src/css/employee_kanban.css`

### 7.3 Organization Chart OWL Component

**Component:** `OrgStructure` (`hcm/static/src/js/org_structure.js:11-215`)

**Configuration:**

| Parameter | Nilai |
|-----------|-------|
| `nodeWidth` | 240 |
| `nodeHeight` | 130 |
| `childrenMargin` | 60 |
| `compactMarginBetween` | 30 |
| `compactMarginPair` | 80 |
| `siblingsMargin` | 20 |

**Node Content:**
- Gradient header (department color)
- Position name
- Department name
- Employee count
- Up to 4 employee names + "more" indicator

**Interactions:**
- Scroll zoom
- Drag pan
- Click expand/collapse

**CDN Dependencies:**

| Library | Versi | URL |
|---------|-------|-----|
| d3.js | v7 | `https://d3js.org/d3.v7.min.js` |
| d3-flextree | v2.1.2 | `https://cdn.jsdelivr.net/npm/d3-flextree@2.1.2/build/d3-flextree.min.js` |
| d3-org-chart | v2.6.0 | `https://cdn.jsdelivr.net/npm/d3-org-chart@2.6.0/build/d3-org-chart.min.js` |

### 7.4 Many2one Field Injection

**Lokasi:** `sales/models/models.py:12-31` (`_inject_m2o_no_open_create`)

Semua Many2one fields di form views di-inject dengan `no_open=True` dan `no_create=True` untuk mencegah navigasi ke record terkait dan pembelian record baru dari dropdown.

---

## 8. Integration & Email

### 8.1 Email Templates

| Template | Lokasi | Kegunaan |
|----------|--------|----------|
| `email_template_compressor_quotation` | `sales/data/mail_template_data.xml` | Kirim quotation via email |
| `email_template_sales_approval_request` | `sales/data/mail_template_approver.xml` | Notifikasi ke approver berikutnya |
| `email_template_sales_invoice` | `sales/data/mail_template_data.xml` | Kirim invoice via email (dengan PDF attachment) |

### 8.2 Mail Compose Message Extension

**Model:** `mail.compose.message` (inherited) — `sales/models/models.py:280-309`

| Field | Tipe | Keterangan |
|-------|------|------------|
| `customer_ids` | Many2many → `sales.customer` | Custom field |

**Behavior:**
- `_onchange_customer_ids()` (line 291): Sync `customer_ids` ke `partner_ids` untuk email
- `send_mail()` (line 299): Setelah kirim, redirect ke tree action jika `redirect_to_tree` di context

### 8.3 Integration Points

| Dari | Ke | Mekanisme |
|------|----|-----------|
| sales.customer | res.partner | Auto-create/update/delete on CRUD |
| sales.customer | ir.attachment | Document repository |
| sales.invoice | ir.attachment | PDF invoice attachment |
| sales.invoice | mail.compose.message | Email kirim invoice |
| sales.sales_order | mail.compose.message | Email quotation |
| sales.sales_order | email_template_sales_approval_request | Email approval notification |
| hcm.employee | ir.attachment | Document repository |
| hcm.employee | general.custom_users | User link |

### 8.4 Quotation Email Flow

```
User klik "Send by Email"
    │
    ├── Open mail.compose.window
    │   ├── Pre-fill: customer email via partner_id
    │   └── Template: email_template_compressor_quotation
    │
    ├── User review & kirim
    │
    └── _message_post_after_hook()
        └── Set state = 'sent' (dari draft atau approved)
```

### 8.5 Approval Notification Flow

```
SO di-submit untuk approval
    │
    └── _send_approval_notification()
        ├── Find first pending log
        ├── Get approver email
        └── Send email via email_template_sales_approval_request
            ├── Subject: "Approval Required: {sales_code}"
            ├── Body: SO details
            └── Recipient: approver email
```

---

## 9. Referensi File

### 9.1 File Utama

| File | Purpose |
|------|---------|
| `disable_autosave/__manifest__.py` | Module manifest |
| `disable_autosave/static/src/js/disable_autosave.js` | Cancel button handler, auto-save patch |
| `disable_autosave/static/src/css/disable_autosave.css` | Cancel button styling |
| `general/__manifest__.py` | Module manifest |
| `general/models/models.py` | NavigationMixin, all master data, RBAC (1053 lines) |
| `general/views/views.xml` | Form/tree views |
| `general/data/menu.xml` | Menu structure |
| `general/data/home.xml` | Home dashboard view |
| `general/data/sequence.xml` | ID sequences |
| `general/security/ir.model.access.csv` | Model-level access control |
| `hcm/__manifest__.py` | Module manifest |
| `hcm/models/models.py` | Position, Employee, Family, Education, etc. (457 lines) |
| `hcm/views/views.xml` | Form/tree views, actions, menus |
| `hcm/views/templates.xml` | Position org tree view |
| `hcm/static/src/js/org_structure.js` | Org chart OWL component (215 lines) |
| `hcm/static/src/xml/org_structure.xml` | Org chart template |
| `hcm/static/src/css/employee_kanban.css` | Kanban styling |
| `hcm/data/sequence.xml` | HCM ID sequences |
| `hcm/data/menu.xml` | HCM menu structure |
| `hcm/security/ir.model.access.csv` | HCM access control |
| `sales/__manifest__.py` | Module manifest |
| `sales/models/models.py` | All sales models (3685 lines) |
| `sales/views/views.xml` | Form/tree views |
| `sales/views/templates.xml` | Sales templates |
| `sales/data/menu.xml` | Sales menu structure |
| `sales/data/sequence.xml` | Sales ID sequences |
| `sales/data/account_type.xml` | Account type data |
| `sales/data/product_type.xml` | Product type data |
| `sales/data/activity.xml` | Activity data |
| `sales/data/mail_template_data.xml` | Email templates |
| `sales/data/mail_template_approver.xml` | Approval email template |
| `sales/data/terms_and_conditions.xml` | Default T&C |
| `sales/security/ir.model.access.csv` | Sales access control |
| `user_management/__manifest__.py` | Module manifest |
| `user_management/views/views.xml` | User management UI |

### 9.2 Model Size Summary

| Model | File | Lines | Complexity |
|-------|------|-------|------------|
| `sales.sales_order` | `sales/models/models.py` | 1044-2178 (~1135) | Very High |
| `sales.invoice` | `sales/models/models.py` | 2532-3165 (~633) | High |
| `sales.customer` | `sales/models/models.py` | 312-543 (~231) | Medium |
| `sales.payment` | `sales/models/models.py` | 3360-3482 (~122) | Medium |
| `NavigationMixin` | `general/models/models.py` | 138-348 (~210) | High |
| `hcm.employee` | `hcm/models/models.py` | 55-341 (~286) | Medium |
| `sales.price_condition` | `sales/models/models.py` | 769-888 (~119) | Medium |
| `sales.products` | `sales/models/models.py` | 686-767 (~81) | Low |
| `general.custom_users` | `general/models/models.py` | 748-864 (~116) | Medium |

### 9.3 Sequence Codes

| Sequence Code | Model |
|---------------|-------|
| `general.country.sequence` | `general.country` |
| `general.state.sequence` | `general.state` |
| `general.city.sequence` | `general.city` |
| `general.district.sequence` | `general.district` |
| `general.village.sequence` | `general.village` |
| `general.company.sequence` | `general.company` |
| `general.location.sequence` | `general.location` |
| `general.division.sequence` | `general.division` |
| `general.department.sequence` | `general.department` |
| `general.position.sequence` | `general.position` |
| `general.level_grade.sequence` | `general.level_grade` |
| `general.custom_users_sequence` | `general.custom_users` |
| `hcm.position.sequence` | `hcm.position` |
| `hcm.employee.sequence` | `hcm.employee` |
| `sales.cust_category` | `sales.cust_category` |
| `sales.cust_type` | `sales.cust_type` |
| `sales.cust_area` | `sales.cust_area` |
| `sales.customer` | `sales.customer` |
| `sales.ship_to` | `sales.ship_to` |
| `sales.product` | `sales.products` |
| `sales.price_condition` | `sales.price_condition` |
| `sales.payment_terms` | `sales.payment_terms` |
| `sales.sales_order` | `sales.sales_order` |
| `sales.invoice` | `sales.invoice` |
| `sales.payment` | `sales.payment` |
| `sales.delivery` | `sales.delivery` |

---

*Document generated from ERP KSI codebase analysis.*
