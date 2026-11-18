# Deploy ERP dengan Docker

Stack: Odoo 17 (`erp-odoo:latest`, dibangun dari repo ini) + PostgreSQL 18.
Odoo hanya mendengarkan di `127.0.0.1`, jadi pasang reverse proxy (contoh
Nginx: `docker/nginx.conf.example`) untuk domain dan HTTPS.

## 1. Persiapan VPS

```bash
# Docker Engine + plugin compose (Ubuntu 22.04/24.04)
curl -fsSL https://get.docker.com | sh
git clone <repo> erp && cd erp
cp .env.example .env
nano .env          # ganti SEMUA password, sesuaikan ODOO_WORKERS dengan jumlah vCPU
```

## 2a. Server baru (database kosong)

Biarkan `ODOO_INIT_MODULES=general,hcm,sales,user_management` di `.env`.
Saat start pertama, database `erp` dibuat dan modul dipasang otomatis
(bahasa Indonesia + Inggris aktif, Indonesia jadi bahasa admin).

```bash
docker compose up -d --build
docker compose logs -f odoo      # tunggu "Modules loaded"
```

Login awal: `admin` / `admin` — langsung ganti password-nya.

## 2b. Pindah data dari server lain

Kosongkan `ODOO_INIT_MODULES=` di `.env`, lalu:

```bash
# Di server lama
pg_dump --format=plain --no-owner --no-privileges erp > erp.sql
tar -C "<data_dir>/filestore" -czf filestore.tgz erp
# (macOS: data_dir = ~/Library/Application Support/Odoo)

# Di VPS (salin erp.sql dan filestore.tgz ke folder repo)
docker compose up -d db
docker compose exec -T db createdb -U odoo erp
docker compose exec -T db psql -U odoo -d erp -q -v ON_ERROR_STOP=1 < erp.sql
gunzip -c filestore.tgz | docker compose run --rm -T --no-deps --user root \
  --entrypoint sh odoo -c 'mkdir -p /var/lib/odoo/filestore && tar -xf - -C /var/lib/odoo/filestore && chown -R odoo:odoo /var/lib/odoo'
docker compose run --rm --no-deps odoo odoo -u general,hcm,sales,user_management --stop-after-init --workers=0
docker compose up -d
```

`pg_dump` dari PostgreSQL 18 tidak bisa dipulihkan ke versi yang lebih lama,
karena itu image database dikunci ke `postgres:18`.

## 3. Update aplikasi

```bash
git pull
docker compose build odoo
docker compose run --rm --no-deps odoo odoo -u general,hcm,sales,user_management --stop-after-init --workers=0
docker compose up -d
```

## 4. Backup harian

```bash
docker compose exec -T db pg_dump -U odoo --format=custom erp > backup/erp_$(date +%F).dump
docker compose run --rm --no-deps --entrypoint tar odoo -czf - -C /var/lib/odoo/filestore erp > backup/filestore_$(date +%F).tgz
```

Simpan hasil backup di luar VPS (object storage / server lain).

## Variabel penting (`.env`)

| Variabel | Default | Keterangan |
|---|---|---|
| `ODOO_WORKERS` | 3 | Maks (2 × vCPU) + 1. `0` hanya untuk development |
| `ODOO_LIMIT_MEMORY_SOFT/HARD` | 640/768 MB | Batas memori per worker |
| `ODOO_INIT_MODULES` | kosong | Modul yang dipasang bila database belum ada |
| `ODOO_LOAD_LANGUAGE` | `id_ID,en_US` | Bahasa saat database baru dibuat |
| `ODOO_HTTP_PORT` / `ODOO_GEVENT_PORT` | 8017 / 8072 | Port di host (127.0.0.1) |
