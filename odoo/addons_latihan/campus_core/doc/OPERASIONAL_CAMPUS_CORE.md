# Dokumentasi Operasional — Campus Core

**Modul:** `campus_core` (Integrated Campus Management System - Core)
**Versi:** 19.0.2.0.0
**Platform:** Odoo 19
**Kategori:** Education

Dokumen ini adalah panduan operasional lengkap untuk modul **Campus Core** beserta
ekstensi penilaian **Campus Academic**. Mencakup arsitektur data, hak akses, alur
kerja KRS, aturan bisnis, dan panduan penggunaan langkah demi langkah.

---

## 1. Ruang Lingkup

Campus Core adalah modul inti Sistem Informasi Akademik / KRS yang mengelola:

- **Master Data Struktur Kampus** — hierarki **Fakultas → Program Studi → Jurusan**.
- **Master Data Mahasiswa** — biodata + data akademik + status kelulusan.
- **Master Data Dosen** — terikat pada struktur kampus.
- **Master Data Mata Kuliah & Kelas** — jadwal + kuota per kelas.
- **KRS / Enrollment** — pemilihan kelas berbasis kuota (FCFS), validasi jadwal
  bentrok & SKS, workflow persetujuan Mahasiswa ↔ Dosen.

Modul pelengkap **`campus_academic`** menambahkan:

- **Transkrip Nilai** — input nilai angka (0–100) yang otomatis dikonversi ke
  nilai huruf + bobot, perhitungan IPK, dan rekap SKS lulus untuk validasi kelulusan.
- **Laporan cetak Transkrip Nilai** (PDF).

---

## 2. Instalasi & Upgrade

Modul berada di `odoo/addons_latihan/`. Path tersebut sudah terdaftar di `odoo.conf`
(`addons_path`).

### Lewat UI
1. Masuk sebagai Administrator.
2. **Apps** → hapus filter "Apps" → cari **"Integrated Campus Management System - Core"**.
3. Klik **Activate/Install**. Untuk memperbarui setelah ada perubahan kode:
   buka modul → **Upgrade**.
4. (Opsional) Install **"Campus Academic"** untuk fitur Transkrip & penilaian.

### Lewat command line
```bash
python odoo-bin -c odoo.conf -u campus_core,campus_academic -d <nama_db> --stop-after-init
```

> **Catatan migrasi data lama:**
> - FK `fakultas_id` / `prodi_id` / `jurusan_id` pada Mahasiswa & Dosen bersifat
>   *nullable* di database (wajib hanya di form input), sehingga upgrade tidak gagal
>   bila sudah ada record lama. Lengkapi struktur record lama secara manual.
> - Pada Transkrip, `nilai_huruf` kini dihitung dari `nilai_angka` (default 0 → E).
>   Isi ulang kolom **Nilai Angka** untuk data lama.

---

## 3. Struktur Menu

```
Campus Management
├── Academic
│   ├── KRS Enrollment            (campus.krs)
│   └── Transkrip Nilai           (campus.transkrip)      ← dari campus_academic
└── Master Data
    ├── Struktur Kampus
    │   ├── Fakultas              (campus.fakultas)
    │   ├── Program Studi         (campus.prodi)
    │   └── Jurusan               (campus.jurusan)
    ├── Mahasiswa                 (campus.mahasiswa)
    ├── Dosen                     (campus.dosen)
    ├── Mata Kuliah               (campus.mata_kuliah)
    └── Kelas                     (campus.kelas)
```

---

## 4. Arsitektur Data (Model & Relasi)

### 4.1 Hierarki Struktur Kampus — Fakultas → Prodi → Jurusan

```
campus.fakultas (1) ──< campus.prodi (1) ──< campus.jurusan
   Fakultas                Program Studi          Jurusan (leaf)
```

| Model | Field kunci | Relasi |
|-------|-------------|--------|
| `campus.fakultas` | `kode`, `name` | `prodi_ids` (One2many) |
| `campus.prodi` | `kode`, `name`, `jenjang` | `fakultas_id` (M2o, induk), `jurusan_ids` (One2many) |
| `campus.jurusan` | `kode`, `name` | `prodi_id` (M2o, induk), `fakultas_id` (related, otomatis) |

- 1 **Fakultas** memiliki banyak **Program Studi**.
- 1 **Program Studi** memiliki banyak **Jurusan**.
- **Jurusan** adalah level paling bawah; `fakultas_id`-nya terisi otomatis mengikuti
  Prodi induknya.
- `kode` di tiap level bersifat **unik**.

### 4.2 Mahasiswa (`campus.mahasiswa`)

| Kelompok | Field |
|----------|-------|
| Identitas | `nim` (unik), `name`, `tempat_lahir`, `tanggal_lahir`, `jenis_kelamin` (L/P), `alamat` |
| Akademik | `fakultas_id`, `prodi_id`, `jurusan_id`, `angkatan`, `semester_aktif`, `ipk`, `status` (aktif/non-aktif/lulus/cuti) |
| Kelulusan | `total_sks_lulus`, `status_kelulusan` (belum/lulus) |

- FK struktur kampus **wajib diisi di form** (cascading: pilih Fakultas → Prodi → Jurusan).
- `total_sks_lulus` terisi **otomatis** dari transkrip ber-status *Approved* bila
  modul `campus_academic` terpasang.

### 4.3 Dosen (`campus.dosen`)

`nip` (unik), `name`, dan FK **`fakultas_id` → `prodi_id` → `jurusan_id`** (wajib di form).
Dosen "terikat" pada struktur hierarki kampus.

### 4.4 Mata Kuliah (`campus.mata_kuliah`) & Kelas (`campus.kelas`)

**Mata Kuliah:** `kode_mk` (unik), `name`, `sks` (> 0), `dosen_id`, FK struktur
(`fakultas_id`/`prodi_id`/`jurusan_id`), dan `kelas_ids`.

**Cakupan pengambilan mata kuliah (bertingkat):**
- **Fakultas wajib diisi**; Prodi & Jurusan opsional.
- Hanya **Fakultas** terisi → mata kuliah ranah fakultas: **semua mahasiswa di
  fakultas itu** boleh mengambil.
- **Fakultas + Prodi** terisi (Jurusan kosong) → ranah prodi: hanya mahasiswa di
  **prodi** tersebut.
- **Fakultas + Prodi + Jurusan** terisi → ranah jurusan: hanya mahasiswa di
  **jurusan** tersebut.

Saat menyusun KRS, daftar kelas otomatis difilter sesuai struktur mahasiswa
(field `allowed_kelas_ids`), dan dicek ulang (hard validation) saat **Submit**.

**Kelas** (offering yang membedakan jadwal & kuota — Kelas A/B/C):

| Kelompok | Field |
|----------|-------|
| Identitas | `name` (A/B/C), `mata_kuliah_id`, `semester`, `dosen_id`, `sks` (related) |
| Jadwal | `hari`, `jam_mulai`, `jam_selesai`, `ruangan` |
| Kuota (FCFS) | `kuota`, `terisi` (auto), `sisa_kuota` (auto), `is_available` (auto) |

- `terisi` = jumlah peserta yang KRS-nya sudah **Submitted/Processed** dan baris MK-nya
  **tidak** berstatus *Rejected*.
- `is_available = (kuota - terisi) > 0`. Kelas penuh otomatis tidak tampil saat
  mahasiswa memilih.

### 4.5 KRS (`campus.krs`) & Baris KRS (`campus.krs.line`)

**KRS (lembar):** `name` (otomatis: `KRS/<NIM>/<Semester>`), `mahasiswa_id`,
`dosen_pembimbing_id`, `semester`, `line_ids`, `total_sks` (auto),
`state` (**draft → submitted → processed**).

**Baris KRS (per mata kuliah):**

| Field | Keterangan |
|-------|------------|
| `kelas_id` | Kelas yang dipilih (hanya yang `is_available` & semester sama) |
| `mata_kuliah_id`, `sks`, `dosen_id`, `hari`, `jam_*`, `ruangan` | otomatis (related dari Kelas) |
| `state` | **pending → approved / rejected** (diatur Dosen) |

---

## 5. Role & Hak Akses

Dua grup keamanan dibuat (Settings → Users & Companies → Groups):

| Grup | XML ID | Peran |
|------|--------|-------|
| **Campus / Student (Mahasiswa)** | `campus_core.group_campus_student` | Menyusun & mengunci (submit) KRS |
| **Campus / Lecturer (Dosen Pembimbing)** | `campus_core.group_campus_lecturer` | Memeriksa KRS: menyetujui/menolak tiap mata kuliah, lalu memproses KRS |

- Lecturer mewarisi (implies) hak Student.
- Pembatasan diterapkan pada **tombol**:
  - Tombol **Submit KRS** → hanya Student.
  - Tombol **Proses KRS** + tombol **Setujui/Tolak** per baris → hanya Lecturer.

> Tetapkan grup ke user lewat **Settings → Users → (pilih user) → tab Other/Extra Rights**.

---

## 6. Panduan Operasional (Langkah demi Langkah)

### Langkah 0 — Siapkan Master Struktur Kampus (urutan WAJIB)
1. **Master Data → Struktur Kampus → Fakultas** → buat Fakultas (mis. *FT — Fakultas Teknik*).
   Di dalam form Fakultas, tab **Program Studi** bisa langsung menambah Prodi.
2. **Program Studi** → pastikan tiap Prodi punya `fakultas_id`, `jenjang`, lalu di tab
   **Jurusan** tambahkan Jurusan-nya.
3. **Jurusan** → level terakhir; `fakultas_id` terisi otomatis dari Prodi.

### Langkah 1 — Input Dosen
**Master Data → Dosen** → isi NIP, Nama, lalu pilih **Fakultas → Prodi → Jurusan**
(berurutan; dropdown menyaring otomatis).

### Langkah 2 — Input Mahasiswa
**Master Data → Mahasiswa** → isi biodata, **Fakultas → Prodi → Jurusan**, Angkatan,
Semester Aktif. `status_kelulusan` default **Belum Lulus**.

### Langkah 3 — Input Mata Kuliah & Kelas
1. **Master Data → Mata Kuliah** → isi Kode MK, Nama, SKS, Dosen, struktur.
2. Di tab **Kelas & Jadwal**, tambahkan kelas: `name` (A/B/C), `semester`
   (mis. *Semester Gasal 2025/2026*), Dosen, **Hari**, **Jam Mulai/Selesai**, **Ruangan**,
   dan **Kuota**.
   - Format jam memakai widget `float_time`: ketik `08:30` (disimpan 8.5).

### Langkah 4 — Mahasiswa Menyusun KRS *(role: Student)*
1. **Academic → KRS Enrollment → New**.
2. Pilih **Mahasiswa**, **Dosen Pembimbing**, dan **Semester**
   (mis. *Semester Gasal 2025/2026* — harus sama dengan semester kelas).
3. Tab **Mata Kuliah Terpilih** → tambah baris → pilih **Kelas**
   (hanya kelas yang masih *available* & semester cocok yang muncul).
4. Klik **Submit KRS**. Sistem memvalidasi (lihat Bab 7). Jika lolos, status → **Submitted**
   dan kuota kelas terkunci untuk mahasiswa ini.

### Langkah 5 — Dosen Memeriksa KRS *(role: Lecturer)*
1. Buka KRS ber-status **Submitted**.
2. Pada tiap baris mata kuliah, klik **Setujui** (✓) atau **Tolak** (✗) →
   status baris menjadi *Approved* / *Rejected*.
3. Setelah semua baris diputuskan (tidak ada *Pending*), klik **Proses KRS** →
   status lembar → **Processed**.

> Selama masih **Submitted**, KRS dapat dikembalikan ke **Draft** (tombol *Kembali Ke Draft*)
> untuk revisi; semua baris di-reset ke *Pending*. KRS yang sudah **Processed** terkunci.

### Langkah 6 — Input Nilai & Transkrip *(campus_academic)*
1. **Academic → Transkrip Nilai → New** → pilih Mahasiswa & Semester.
2. Tambah baris nilai: pilih **Mata Kuliah**, isi **Nilai Angka** (0–100).
   Nilai Huruf, Bobot, Mutu, dan status Lulus MK terisi otomatis.
3. **Submit → Approve**. Transkrip *Approved* tidak bisa diubah/dihapus dan
   ikut menambah `total_sks_lulus` mahasiswa.
4. Klik **Cetak Transkrip** untuk PDF.

---

## 7. Aturan Bisnis & Validasi

| # | Aturan | Kapan dicek | Pesan bila gagal |
|---|--------|-------------|------------------|
| 1 | **Maksimal 24 SKS** per KRS | constraint `total_sks` | "Total SKS (…) melebihi batas maksimum 24 SKS!" |
| 2 | **1 kelas per mata kuliah** dalam satu KRS | constraint `line_ids` | "Setiap mata kuliah hanya boleh diambil 1 kelas…" |
| 3 | **Jadwal tidak boleh bentrok** (hari sama + jam beririsan) | saat **Submit** | "Jadwal bentrok antara '…' dan '…'." |
| 4 | **Kuota kelas** masih tersedia (FCFS / rebutan) | saat **Submit** + filter pemilihan | "Kelas '…' sudah penuh (kuota …)." |
| 5 | **Minimal 1 mata kuliah** sebelum submit | saat **Submit** | "Anda harus memilih minimal satu Mata Kuliah…" |
| 5b | **Cakupan MK sesuai struktur mahasiswa** (Fakultas/Prodi/Jurusan) | filter pemilihan + saat **Submit** | "Mata kuliah '…' tidak tersedia untuk mahasiswa ini…" |
| 6 | **Semua baris diputuskan** sebelum Proses | saat **Proses** | "Masih ada … mata kuliah berstatus Pending…" |
| 7 | **Kelulusan ≥ 144 SKS** | constraint Mahasiswa | "…belum memenuhi syarat kelulusan. Total SKS lulus …, minimal 144 SKS." |
| 8 | **SKS mata kuliah > 0** | constraint Mata Kuliah | "SKS harus lebih besar dari 0!" |
| 9 | **Jam selesai > jam mulai** | constraint Kelas | "Jam Selesai harus lebih besar dari Jam Mulai…" |
| 10 | **Nilai angka 0–100** | constraint Transkrip Nilai | "Nilai angka harus di rentang 0 - 100!" |

### 7.1 Sistem Kuota FCFS (First-Come-First-Served / Rebutan)
- Kelas **draft** belum memakai kuota. Kuota baru terkunci saat KRS **Submit**.
- Bila dua mahasiswa memperebutkan kursi terakhir, **yang submit lebih dulu** mendapat
  kursi; yang berikutnya ditolak saat submit dengan pesan kelas penuh.

### 7.2 Skala Penilaian (angka → huruf → bobot)
Konversi otomatis pada `campus.transkrip.nilai`:

| Nilai Angka | Huruf | Bobot |
|-------------|-------|-------|
| ≥ 85 | **A** | 4.0 |
| 80 – 84.99 | **B+** | 3.5 |
| 75 – 79.99 | **B** | 3.0 |
| 70 – 74.99 | **C+** | 2.5 |
| 60 – 69.99 | **C** | 2.0 |
| 50 – 59.99 | **D** | 1.0 |
| < 50 | **E** | 0.0 |

- **Nilai Mutu** = Bobot × SKS. **IPK** = Σ Nilai Mutu ÷ Σ SKS.
- **Lulus MK** = huruf ≠ E (nilai ≥ 50). Hanya SKS lulus yang dihitung ke `total_sks_lulus`.

### 7.3 Status Kelulusan
- Default **Belum Lulus**.
- Hanya bisa diubah menjadi **Lulus** bila `total_sks_lulus ≥ 144` (divalidasi constraint).

---

## 8. Diagram Status (State Machine)

**KRS (lembar) — status makro:**
```
draft ──Submit(Student)──> submitted ──Proses(Lecturer)──> processed
  ^                            │
  └────Kembali ke Draft────────┘
```

**Baris KRS (per mata kuliah) — status mikro:**
```
pending ──Setujui(Lecturer)──> approved
   │
   └────Tolak(Lecturer)──────> rejected
```

**Transkrip (campus_academic):**
```
draft ──Submit──> submitted ──Approve──> approved (terkunci)
```

---

## 9. Terminologi Penulisan Semester

Gunakan format: **"Semester Gasal 2025/2026"** atau **"Semester Genap 2025/2026"**.
Nilai `semester` pada **Kelas** dan **KRS** harus **sama persis** agar kelas muncul
saat penyusunan KRS.

---

## 10. FAQ / Troubleshooting

**Q: Saat memilih Kelas di KRS, daftarnya kosong.**
A: Pastikan (1) field **Semester** di KRS sudah diisi dan sama persis dengan semester
pada Kelas, dan (2) kelas masih *available* (kuota belum penuh).

**Q: Tombol Submit / Setujui tidak muncul.**
A: Tombol dibatasi role. Submit butuh grup *Student*; Setujui/Tolak/Proses butuh grup
*Lecturer*. Atur lewat Settings → Users.

**Q: Upgrade gagal karena kolom NOT NULL pada data lama.**
A: FK struktur sengaja dibuat nullable di DB. Jika tetap error, kosongkan/isi dulu data
bermasalah, lalu upgrade ulang.

**Q: IPK / SKS Lulus mahasiswa tidak berubah.**
A: `total_sks_lulus` hanya menghitung transkrip ber-status **Approved**. Pastikan transkrip
sudah di-*Approve* dan setiap baris nilainya ≥ 50 (Lulus MK).

**Q: Format jam.**
A: Field jam memakai `float_time`. Ketik `13:30`; tersimpan sebagai `13.5`.

---

## 11. Glosarium

| Istilah | Arti |
|---------|------|
| **KRS** | Kartu Rencana Studi — daftar mata kuliah yang diambil per semester |
| **FCFS** | First-Come-First-Served — sistem rebutan kuota kelas |
| **SKS** | Satuan Kredit Semester |
| **IPK** | Indeks Prestasi Kumulatif |
| **Prodi** | Program Studi |
| **Bentrok** | Dua kelas berjadwal di hari sama dengan rentang jam beririsan |
| **Submitted** | KRS sudah dikunci mahasiswa, menunggu pemeriksaan dosen |
| **Processed** | KRS sudah selesai diperiksa & diproses dosen |

---

## 12. Ringkasan Berkas Modul

```
campus_core/
├── __manifest__.py
├── models/
│   ├── struktur_kampus.py   # Fakultas, Prodi, Jurusan
│   ├── mahasiswa.py         # + biodata, struktur, kelulusan
│   ├── dosen.py             # + struktur FK
│   ├── mata_kuliah.py       # + struktur FK, relasi Kelas
│   ├── kelas.py             # jadwal, kuota FCFS, deteksi bentrok
│   └── krs.py               # KRS + baris, workflow, validasi
├── security/
│   ├── campus_security.xml  # grup Student & Lecturer
│   └── ir.model.access.csv
├── views/                   # struktur, mahasiswa, dosen, mata_kuliah, kelas, krs, menus
└── doc/
    └── OPERASIONAL_CAMPUS_CORE.md   # dokumen ini
```

*Modul pelengkap `campus_academic` menambahkan Transkrip Nilai, konversi nilai,
perhitungan IPK & SKS lulus, serta laporan cetak transkrip.*
